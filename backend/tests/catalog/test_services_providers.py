from unittest.mock import MagicMock, patch

import pytest

from books.models import Author, Book
from books.services import (
    GoogleBooksProvider,
    OpenLibraryProvider,
    WikipediaProvider,
    import_multiple_by_title,
)


@pytest.mark.django_db
class TestModularBookProviders:
    def test_google_books_provider_search(self):
        provider = GoogleBooksProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'id': 'g123',
                    'volumeInfo': {
                        'title': 'El Quijote',
                        'authors': ['Miguel de Cervantes'],
                        'description': 'Clásico de la literatura española',
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9788415448006'}],
                        'imageLinks': {'thumbnail': 'http://books.google.com/quijote.jpg'},
                    },
                }
            ]
        }

        with patch('requests.get', return_value=mock_response):
            results = provider.search_by_title('El Quijote')

        assert len(results) == 1
        dto = results[0]
        assert dto.title == 'El Quijote'
        assert dto.author_name == 'Miguel de Cervantes'
        assert dto.isbn == '9788415448006'
        assert dto.google_volume_id == 'g123'
        assert dto.cover_url == 'http://books.google.com/quijote.jpg'

    def test_openlibrary_provider_search(self):
        provider = OpenLibraryProvider()
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'docs': [
                {
                    'title': 'Cien años de soledad',
                    'author_name': ['Gabriel García Márquez'],
                    'first_publish_year': 1967,
                    'key': '/works/OL123W',
                    'edition_key': ['OL456M'],
                    'cover_i': 78910,
                }
            ]
        }

        with patch('requests.get', return_value=mock_response):
            results = provider.search_by_title('Cien años de soledad')

        assert len(results) == 1
        dto = results[0]
        assert dto.title == 'Cien años de soledad'
        assert dto.author_name == 'Gabriel García Márquez'
        assert dto.published_date_raw == '1967'
        assert dto.openlibrary_work_id == '/works/OL123W'
        assert dto.openlibrary_edition_id == 'OL456M'
        assert '78910-L.jpg' in (dto.cover_url or '')

    def test_wikipedia_provider_search(self):
        provider = WikipediaProvider()
        mock_search_res = MagicMock()
        mock_search_res.ok = True
        mock_search_res.json.return_value = {
            'query': {'search': [{'title': 'Rayuela'}]}
        }

        mock_summary_res = MagicMock()
        mock_summary_res.ok = True
        mock_summary_res.json.return_value = {
            'title': 'Rayuela',
            'description': 'novela por Julio Cortázar',
            'extract': 'Novela contranovela de 1963...',
            'originalimage': {'source': 'https://upload.wikimedia.org/rayuela.jpg'},
        }

        def side_effect(url, **kwargs):
            if 'api.php' in url:
                return mock_search_res
            return mock_summary_res

        with patch('requests.get', side_effect=side_effect):
            results = provider.search_by_title('Rayuela')

        assert len(results) == 1
        dto = results[0]
        assert dto.title == 'Rayuela'
        assert dto.author_name == 'Julio Cortázar'
        assert 'contranovela' in (dto.description or '')

    def test_fallback_flow_when_google_fails(self):
        # Simula fallo 429 de Google Books con fallback a OpenLibrary
        mock_gb_res = MagicMock()
        mock_gb_res.status_code = 429

        mock_ol_res = MagicMock()
        mock_ol_res.ok = True
        mock_ol_res.json.return_value = {
            'docs': [
                {
                    'title': 'Ficciones',
                    'author_name': ['Jorge Luis Borges'],
                    'first_publish_year': 1944,
                    'key': '/works/OL999W',
                }
            ]
        }

        def side_effect(url, **kwargs):
            if 'googleapis' in url:
                return mock_gb_res
            if 'wikipedia' in url:
                # Simula sin resultados en wiki
                empty_wiki = MagicMock()
                empty_wiki.ok = True
                empty_wiki.json.return_value = {'query': {'search': []}}
                return empty_wiki
            if 'openlibrary' in url:
                return mock_ol_res
            return MagicMock(ok=False)

        with patch('requests.get', side_effect=side_effect):
            books = import_multiple_by_title('Ficciones')

        assert len(books) >= 1
        assert books[0].title == 'Ficciones'
        assert books[0].author.name == 'Jorge Luis Borges'
        assert books[0].openlibrary_work_id == '/works/OL999W'

    def test_deduplication_preserves_external_ids(self):
        author = Author.objects.create(name='Isabel Allende')
        existing = Book.objects.create(title='La casa de los espíritus', author=author)

        mock_gb_res = MagicMock()
        mock_gb_res.status_code = 200
        mock_gb_res.json.return_value = {
            'items': [
                {
                    'id': 'google_allende_123',
                    'volumeInfo': {
                        'title': 'La casa de los espíritus',
                        'authors': ['Isabel Allende'],
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9788497592208'}],
                    },
                }
            ]
        }

        with patch('requests.get', return_value=mock_gb_res):
            books = import_multiple_by_title('La casa de los espíritus')

        assert len(books) == 1
        assert books[0].id == existing.id
        existing.refresh_from_db()
        assert existing.google_volume_id == 'google_allende_123'
        assert existing.isbn == '9788497592208'
