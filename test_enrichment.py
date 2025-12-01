import requests
import unicodedata
import logging

# Mock constants
OPEN_LIBRARY_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OPEN_LIBRARY_COVERS_URL = 'https://covers.openlibrary.org'
WIKIPEDIA_API_URL = 'https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts|pageimages&exintro&explaintext&redirects=1&format=json&pithumbsize=500&titles='
WIKIPEDIA_OPENSEARCH_URL = 'https://{lang}.wikipedia.org/w/api.php'

class MockAuthor:
    def __init__(self, name):
        self.name = name
        self.biography = None
        self.photo = None
    
    def save(self):
        print(f"SAVED: Bio length={len(self.biography) if self.biography else 0}, Photo={self.photo}")

def slugify(value):
    return value.lower().replace(' ', '-')

def _download_and_attach_image(instance, field_name, url, filename_hint):
    print(f"DOWNLOAD IMAGE: {url} -> {filename_hint}")
    instance.photo = url

def test_openlibrary(author):
    print(f"--- Testing OpenLibrary for {author.name} ---")
    try:
        rs = requests.get(OPEN_LIBRARY_AUTHORS_URL, params={'q': author.name}, timeout=15)
        rs.raise_for_status()
        data = rs.json()
        docs = data.get('docs') or []
        
        print(f"Found {len(docs)} docs")
        
        if not docs:
            return

        def _norm(s: str) -> str:
            if not s: return ""
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').casefold().strip()
        
        target = _norm(author.name)
        best = None
        
        for d in docs:
            nm = d.get('name')
            print(f"Checking doc: {nm}")
            if nm and _norm(nm) == target:
                best = d
                print("Found exact match!")
                break
        
        if not best:
            for d in docs:
                alts = d.get('alternate_names') or []
                if any(_norm(alt) == target for alt in alts):
                    best = d
                    print("Found alternate name match!")
                    break
        
        if not best and docs:
             first_name = _norm(docs[0].get('name', ''))
             if target in first_name or first_name in target:
                 best = docs[0]
                 print("Found fuzzy match (first result)!")

        if not best:
            print("No match found.")
            return

        olid = best.get('key')
        print(f"OLID: {olid}")

        if olid:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
            if rd.ok:
                detail = rd.json()
                bio = detail.get('bio')
                if isinstance(bio, dict):
                    bio = bio.get('value')
                if bio:
                    print(f"Bio found: {bio[:100]}...")
                    author.biography = bio

        photo_id = None
        photos = best.get('photos') or []
        if photos:
            photo_id = photos[0]
        
        if photo_id:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photo_id}-L.jpg'
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg"
            )
    except Exception as e:
        print(f"Error: {e}")

def test_wikipedia(author):
    print(f"--- Testing Wikipedia for {author.name} ---")
    try:
        name = author.name
        data = None
        headers = {'User-Agent': 'MyBookConnect/1.0 (contact@example.com)', 'Accept': 'application/json'}
        for lang in ('es', 'en'):
            print(f"Trying lang: {lang}")
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            try:
                r = requests.get(url, timeout=10, headers=headers)
                if r.ok:
                    data_json = r.json()
                    pages = data_json.get('query', {}).get('pages', {})
                    for pid, pdata in pages.items():
                        if pid == '-1': continue
                        if 'extract' in pdata:
                            print(f"Found page: {pdata.get('title')}")
                            # Check disambiguation
                            desc = pdata.get('description', '').lower() # Note: API might not return description in this endpoint without proper params, but extract usually hints it.
                            # Actually the API call above uses 'extracts', so we check extract content for "may refer to" or similar if needed, but usually 'pageprops' helps.
                            # For this simple test, we assume if we got an extract it's good unless it's very short.
                            data = pdata
                            break
            except Exception as e:
                print(f"Error direct: {e}")

            if data: break

            # Strategy 2: OpenSearch
            print("Trying OpenSearch...")
            sr_url = WIKIPEDIA_OPENSEARCH_URL.format(lang=lang)
            try:
                sr = requests.get(sr_url, params={'action': 'opensearch', 'search': name, 'limit': 3, 'namespace': 0, 'format': 'json'}, timeout=10, headers=headers)
                if sr.ok:
                    sdata = sr.json()
                    titles = sdata[1] if isinstance(sdata, list) and len(sdata) > 1 else []
                    print(f"OpenSearch titles: {titles}")
                    
                    for title in titles:
                        if "bibliografía" in title.lower() or "bibliography" in title.lower():
                            continue
                        
                        print(f"Checking title: {title}")
                        rr_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(title)
                        rr = requests.get(rr_url, timeout=10, headers=headers)
                        if rr.ok:
                            data_json = rr.json()
                            pages = data_json.get('query', {}).get('pages', {})
                            for pid, pdata in pages.items():
                                if pid == '-1': continue
                                if 'extract' in pdata:
                                    data = pdata
                                    break
                        if data: break
            except Exception as e:
                print(f"Error opensearch: {e}")
            
            if data: break

        if not data:
            print("No Wikipedia data found.")
            return

        extract = data.get('extract')
        if extract:
            print(f"Wiki Bio found: {extract[:100]}...")
            author.biography = extract[:5000]
        
        thumb = data.get('thumbnail')
        if thumb:
            thumb_url = thumb.get('source')
            print(f"Wiki Photo found: {thumb_url}")
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=thumb_url,
                filename_hint=f"{slugify(author.name)}.jpg"
            )
        else:
            print("No Wiki photo found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    a = MockAuthor("Ildefonso Falcones")
    test_openlibrary(a)
    if not a.biography or not a.photo:
        test_wikipedia(a)
