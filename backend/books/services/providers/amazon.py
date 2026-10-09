import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from django.conf import settings
from django.core.cache import cache
import requests

from books.cache_utils import TTL_EXTERNAL_API
from mybookconnect.observability import ObservabilityMetricsService
from ..base import DEFAULT_HEADERS, ProviderBookData

logger = logging.getLogger(__name__)


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(('AWS4' + key).encode('utf-8'), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    k_signing = _sign(k_service, 'aws4_request')
    return k_signing


class AmazonBooksProvider:
    """
    Proveedor para consultar la API oficial de afiliados de Amazon
    (Amazon Product Advertising API v5 - PA-API v5).
    
    Implementa firma criptográfica AWS Signature Version 4 (SigV4) y
    soporte de fallback limpio cuando las credenciales no están configuradas
    o activas en el entorno.
    """

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        tag: str | None = None,
        region: str | None = None,
        host: str | None = None,
        timeout: int = 8,
    ):
        self.access_key = access_key or getattr(settings, 'AMAZON_PAAPI_ACCESS_KEY', '') or ''
        self.secret_key = secret_key or getattr(settings, 'AMAZON_PAAPI_SECRET_KEY', '') or ''
        self.tag = tag or getattr(settings, 'AMAZON_PAAPI_TAG', '') or getattr(settings, 'AMAZON_AFFILIATE_TAG', 'mybooksocial-21')
        self.region = region or getattr(settings, 'AMAZON_PAAPI_REGION', 'eu-west-1')
        self.host = host or getattr(settings, 'AMAZON_PAAPI_HOST', 'webservices.amazon.es')
        self.service = 'ProductAdvertisingAPI'
        self.timeout = timeout

    def is_configured(self) -> bool:
        """Indica si las credenciales de Amazon PA-API están presentes para operar."""
        return bool(self.access_key.strip() and self.secret_key.strip() and self.tag.strip())

    def _build_sigv4_headers(self, target: str, payload_json: str) -> dict[str, str]:
        """Genera los encabezados requeridos con firma SigV4 estándar de AWS."""
        now = datetime.now(timezone.utc)
        amz_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = now.strftime('%Y%m%d')

        canonical_uri = '/paapi5/' + target.split('.')[-1].lower()
        canonical_querystring = ''

        payload_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
        canonical_headers = (
            f'content-encoding:amz-1.0\n'
            f'content-type:application/json; charset=utf-8\n'
            f'host:{self.host}\n'
            f'x-amz-date:{amz_date}\n'
            f'x-amz-target:{target}\n'
        )
        signed_headers = 'content-encoding;content-type;host;x-amz-date;x-amz-target'

        canonical_request = (
            f'POST\n'
            f'{canonical_uri}\n'
            f'{canonical_querystring}\n'
            f'{canonical_headers}\n'
            f'{signed_headers}\n'
            f'{payload_hash}'
        )

        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{self.region}/{self.service}/aws4_request'
        string_to_sign = (
            f'{algorithm}\n'
            f'{amz_date}\n'
            f'{credential_scope}\n'
            f'{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
        )

        signing_key = _get_signature_key(self.secret_key, date_stamp, self.region, self.service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

        authorization_header = (
            f'{algorithm} Credential={self.access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )

        return {
            'content-encoding': 'amz-1.0',
            'content-type': 'application/json; charset=utf-8',
            'host': self.host,
            'x-amz-date': amz_date,
            'x-amz-target': target,
            'Authorization': authorization_header,
            'User-Agent': DEFAULT_HEADERS.get('User-Agent', 'MyBookConnect/1.0'),
        }

    def _parse_item(self, item: dict[str, Any]) -> ProviderBookData:
        """Parsea un Item devuelto por la API PA-API v5 a la estructura ProviderBookData."""
        asin = item.get('ASIN')
        detail_page_url = item.get('DetailPageURL')

        item_info = item.get('ItemInfo', {}) or {}
        title = item_info.get('Title', {}).get('DisplayValue') or 'Desconocido'

        # Extraer autor
        author_name = None
        byline = item_info.get('ByLineInfo', {}) or {}
        contributors = byline.get('Contributors', []) or []
        for c in contributors:
            role = (c.get('Role') or '').lower()
            if 'author' in role or 'autor' in role:
                author_name = c.get('Name')
                break
        if not author_name and contributors:
            author_name = contributors[0].get('Name')

        # Extraer número de páginas
        page_count = None
        tech_info = item_info.get('TechnicalInfo', {}) or {}
        num_pages_data = tech_info.get('NumberOfPages') or {}
        raw_pages = num_pages_data.get('DisplayValue')

        if raw_pages is None:
            prod_info = item_info.get('ProductInfo', {}) or {}
            raw_pages = (prod_info.get('NumberOfPages') or {}).get('DisplayValue')
        if raw_pages is None:
            content_info = item_info.get('ContentInfo', {}) or {}
            raw_pages = (content_info.get('PagesCount') or {}).get('DisplayValue')

        if raw_pages is not None:
            try:
                page_count = int(raw_pages)
                if page_count <= 0:
                    page_count = None
            except (ValueError, TypeError):
                page_count = None

        # Extraer portada en alta resolución
        cover_url = None
        images = item.get('Images', {}) or {}
        primary = images.get('Primary', {}) or {}
        for size in ('HighRes', 'Large', 'Medium'):
            img_data = primary.get(size) or {}
            if img_data.get('URL'):
                cover_url = img_data.get('URL')
                break

        # Extraer fecha de publicación
        published_date_raw = None
        classifications = item_info.get('Classifications', {}) or {}
        pub_date = (item_info.get('ContentInfo', {}) or {}).get('PublicationDate', {})
        if pub_date.get('DisplayValue'):
            published_date_raw = pub_date.get('DisplayValue')

        # Extraer categorías
        categories: list[str] = []
        product_group = classifications.get('ProductGroup', {}).get('DisplayValue')
        if product_group and product_group not in categories:
            categories.append(product_group)

        # Extraer ISBN si está disponible
        isbn = None
        external_ids = item_info.get('ExternalIds', {}) or {}
        isbns = external_ids.get('ISBNs', {}).get('DisplayValues') or []
        if isbns:
            isbn = str(isbns[0])
        elif asin and (len(asin) == 10 and (asin[:-1].isdigit() and (asin[-1].isdigit() or asin[-1].upper() == 'X'))):
            isbn = asin

        return ProviderBookData(
            title=title,
            author_name=author_name,
            isbn=isbn,
            description=None,
            published_date_raw=published_date_raw,
            cover_url=cover_url,
            page_count=page_count,
            asin=asin,
            affiliate_url=detail_page_url,
            categories=categories,
            raw_payload=item,
        )

    def search_by_title(self, title: str, offset: int = 0, limit: int = 8) -> list[ProviderBookData]:
        """
        Busca libros por palabras clave en el catálogo de Amazon Books.
        Si la API no está configurada, retorna de forma limpia e instantánea [].
        """
        if not self.is_configured():
            logger.debug("AmazonBooksProvider no está configurado (faltan credenciales). Saltando búsqueda en Amazon.")
            return []

        clean_title = title.strip()
        if not clean_title:
            return []

        cache_key = f"amazon:paapi:search:{hashlib.md5(f'{clean_title}:{offset}:{limit}'.encode()).hexdigest()}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return [self._parse_item(item) for item in cached]
        except Exception as ce:
            logger.warning(f"Error leyendo caché de Amazon: {ce}")

        page_number = max(1, (offset // 10) + 1)
        item_count = min(max(1, limit), 10)

        payload = {
            'Keywords': clean_title,
            'SearchIndex': 'Books',
            'ItemCount': item_count,
            'ItemPage': page_number,
            'PartnerTag': self.tag,
            'PartnerType': 'Associates',
            'Resources': [
                'ItemInfo.Title',
                'ItemInfo.ByLineInfo',
                'ItemInfo.Classifications',
                'ItemInfo.ContentInfo',
                'ItemInfo.ProductInfo',
                'ItemInfo.TechnicalInfo',
                'ItemInfo.ExternalIds',
                'Images.Primary.Large',
                'Images.Primary.Medium',
                'Offers.Listings.Price',
            ],
        }

        payload_json = json.dumps(payload)
        target = 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems'
        url = f'https://{self.host}/paapi5/searchitems'

        t_start = time.perf_counter()
        try:
            headers = self._build_sigv4_headers(target, payload_json)
            resp = requests.post(url, data=payload_json, headers=headers, timeout=self.timeout)
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            ObservabilityMetricsService.record_external_provider_call('amazon_paapi', success=resp.ok, duration_ms=duration_ms)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get('SearchResult', {}).get('Items', []) or []
                try:
                    cache.set(cache_key, items, timeout=TTL_EXTERNAL_API)
                except Exception as ce:
                    logger.warning(f"Error guardando en caché Amazon: {ce}")
                return [self._parse_item(it) for it in items]

            logger.warning(f"Amazon PA-API devolvió código {resp.status_code}: {resp.text[:200]}")
        except Exception as exc:
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            ObservabilityMetricsService.record_external_provider_call('amazon_paapi', success=False, duration_ms=duration_ms)
            logger.warning(f"Error consultando Amazon PA-API para '{clean_title}': {exc}")

        return []

    def get_by_isbn(self, isbn: str) -> ProviderBookData | None:
        """
        Busca un libro específico por ISBN o ASIN en Amazon.
        Si la API no está configurada, retorna None de forma inmediata.
        """
        if not self.is_configured():
            logger.debug("AmazonBooksProvider no está configurado. Saltando búsqueda por ISBN en Amazon.")
            return None

        clean_isbn = isbn.replace('-', '').replace(' ', '').strip().upper()
        if not clean_isbn:
            return None

        cache_key = f"amazon:paapi:isbn:{clean_isbn}"
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return self._parse_item(cached)
        except Exception as ce:
            logger.warning(f"Error leyendo caché de Amazon ISBN: {ce}")

        payload = {
            'ItemIds': [clean_isbn],
            'ItemIdType': 'ISBN' if len(clean_isbn) in (10, 13) else 'ASIN',
            'PartnerTag': self.tag,
            'PartnerType': 'Associates',
            'Resources': [
                'ItemInfo.Title',
                'ItemInfo.ByLineInfo',
                'ItemInfo.Classifications',
                'ItemInfo.ContentInfo',
                'ItemInfo.ProductInfo',
                'ItemInfo.TechnicalInfo',
                'ItemInfo.ExternalIds',
                'Images.Primary.Large',
                'Images.Primary.Medium',
                'Offers.Listings.Price',
            ],
        }

        payload_json = json.dumps(payload)
        target = 'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems'
        url = f'https://{self.host}/paapi5/getitems'

        t_start = time.perf_counter()
        try:
            headers = self._build_sigv4_headers(target, payload_json)
            resp = requests.post(url, data=payload_json, headers=headers, timeout=self.timeout)
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            ObservabilityMetricsService.record_external_provider_call('amazon_paapi', success=resp.ok, duration_ms=duration_ms)

            if resp.status_code == 200:
                data = resp.json()
                items = data.get('ItemsResult', {}).get('Items', []) or []
                if items:
                    item = items[0]
                    try:
                        cache.set(cache_key, item, timeout=TTL_EXTERNAL_API)
                    except Exception as ce:
                        logger.warning(f"Error guardando en caché Amazon ISBN: {ce}")
                    return self._parse_item(item)

            logger.warning(f"Amazon PA-API GetItems devolvió código {resp.status_code} para ISBN {clean_isbn}")
        except Exception as exc:
            duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            ObservabilityMetricsService.record_external_provider_call('amazon_paapi', success=False, duration_ms=duration_ms)
            logger.warning(f"Error consultando Amazon PA-API para ISBN {clean_isbn}: {exc}")

        return None
