import hashlib
import logging

import requests
from django.utils.text import slugify

from books.models import Author

from .base import (
    DEFAULT_HEADERS,
    OPEN_LIBRARY_AUTHORS_URL,
    OPEN_LIBRARY_COVERS_URL,
    OPENLIBRARY_HEADERS,
    WIKIDATA_ENTITY_URL,
    WIKIDATA_SEARCH_URL,
    WIKIPEDIA_API_URL,
    WIKIPEDIA_OPENSEARCH_URL,
)
from .cover_service import download_and_attach_image

logger = logging.getLogger(__name__)


def maybe_enrich_author(author: Author) -> None:
    """
    Enriquece de forma exhaustiva al autor:
    1. Wikipedia (biografía detallada en español y foto en alta resolución)
    2. Wikidata (como alternativa para retrato o biografía adicional)
    3. OpenLibrary (para fotos adicionales si aún faltan)
    """
    if author.biography and author.photo:
        return

    # 1. Wikipedia primero (más fiable y sin caídas de SSL)
    maybe_enrich_author_from_wikipedia(author)

    # 2. Wikidata si falta foto o bio
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikidata(author)

    # 3. OpenLibrary si todavía falta algo
    if not author.biography or not author.photo:
        maybe_enrich_author_from_openlibrary(author)


def maybe_enrich_author_from_wikipedia(author: Author) -> None:
    """
    Enriquece la información del autor desde Wikipedia usando headers válidos.
    """
    if author.biography and author.photo:
        return

    name = author.name.strip()
    try:
        for lang in ('es', 'en'):
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            r = requests.get(url, timeout=7, headers=DEFAULT_HEADERS)
            if not r.ok:
                # Probar con opensearch
                sr = requests.get(
                    WIKIPEDIA_OPENSEARCH_URL.format(lang=lang),
                    params={'action': 'opensearch', 'search': name, 'limit': 3, 'format': 'json'},
                    timeout=7,
                    headers=DEFAULT_HEADERS,
                )
                if sr.ok:
                    titles = sr.json()[1] if len(sr.json()) > 1 else []
                    for t in titles:
                        sub_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(t)
                        sub_r = requests.get(sub_url, timeout=7, headers=DEFAULT_HEADERS)
                        if sub_r.ok:
                            r = sub_r
                            break

            if r.ok:
                data = r.json()
                desc = data.get('description', '').lower()
                # Verificar que sea persona o escritor
                if 'desambiguación' in desc or 'disambiguation' in desc:
                    continue

                if not author.biography:
                    extract = data.get('extract')
                    if extract:
                        author.biography = extract[:4000]

                if not author.photo:
                    img_data = data.get('originalimage') or data.get('thumbnail') or {}
                    img_url = img_data.get('source')
                    if img_url:
                        download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=img_url,
                            filename_hint=f"{slugify(author.name)}.jpg",
                        )

                if author.biography or author.photo:
                    author.save()
                    break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikipedia: {e}")


def maybe_enrich_author_from_wikidata(author: Author) -> None:
    """
    Enriquece autor desde Wikidata buscando retrato P18 y biografía.
    """
    if author.biography and author.photo:
        return

    try:
        search_params = {
            'action': 'wbsearchentities',
            'search': author.name,
            'language': 'es',
            'type': 'item',
            'format': 'json',
            'limit': 5,
        }
        search_resp = requests.get(WIKIDATA_SEARCH_URL, params=search_params, timeout=7, headers=DEFAULT_HEADERS)
        if not search_resp.ok:
            return

        results = search_resp.json().get('search', [])
        for item in results:
            entity_id = item.get('id')
            entity_url = WIKIDATA_ENTITY_URL.format(entity=entity_id)
            entity_resp = requests.get(entity_url, timeout=7, headers=DEFAULT_HEADERS)
            if not entity_resp.ok:
                continue

            entity_info = entity_resp.json().get('entities', {}).get(entity_id, {})
            claims = entity_info.get('claims', {})

            # Foto P18
            if not author.photo and 'P18' in claims:
                image_claims = claims['P18']
                if image_claims:
                    img_filename = image_claims[0].get('mainsnak', {}).get('datavalue', {}).get('value')
                    if img_filename:
                        clean_fn = img_filename.replace(' ', '_')
                        md5_hash = hashlib.md5(clean_fn.encode('utf-8')).hexdigest()
                        image_url = f"https://upload.wikimedia.org/wikipedia/commons/{md5_hash[0]}/{md5_hash[0:2]}/{requests.utils.quote(clean_fn)}"
                        download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=image_url,
                            filename_hint=f"{slugify(author.name)}_wikidata.jpg",
                        )

            # Descripción / Biografía
            if not author.biography:
                descriptions = entity_info.get('descriptions', {})
                desc = descriptions.get('es', {}).get('value') or descriptions.get('en', {}).get('value')
                if desc:
                    author.biography = f"{author.name}: {desc}"

            if author.biography or author.photo:
                author.save()
                break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikidata: {e}")


def maybe_enrich_author_from_openlibrary(author: Author) -> None:
    """
    Enriquece autor desde OpenLibrary como fallback secundario.
    """
    if author.biography and author.photo:
        return

    try:
        rs = requests.get(
            OPEN_LIBRARY_AUTHORS_URL,
            params={'q': author.name},
            timeout=8,
            headers=OPENLIBRARY_HEADERS,
        )
        if not rs.ok:
            return

        docs = rs.json().get('docs') or []
        if not docs:
            return

        best = docs[0]
        olid = best.get('key')
        if olid and not author.biography:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=6, headers=DEFAULT_HEADERS)
            if rd.ok:
                bio = rd.json().get('bio')
                if isinstance(bio, dict):
                    bio = bio.get('value')
                if bio:
                    author.biography = bio

        photos = best.get('photos') or []
        if photos and not author.photo:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photos[0]}-L.jpg'
            download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg",
            )

        if author.biography or author.photo:
            author.save()

    except Exception as e:
        logger.warning(f"OpenLibrary author enrichment skipped for {author.name}: {e}")
