import os
from unittest.mock import MagicMock, patch

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mybookconnect.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author
from books.services import import_books_by_author


def test_import_books_by_author():
    print("Testing import_books_by_author...")

    # Mock requests.get
    with patch('books.services.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            'items': [
                {
                    'volumeInfo': {
                        'title': 'Test Book 1',
                        'authors': ['Test Author'],
                        'publishedDate': '2023',
                        'description': 'Description 1',
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9781234567890'}]
                    }
                },
                {
                    'volumeInfo': {
                        'title': 'Test Book 2',
                        'authors': ['Test Author'],
                        'publishedDate': '2022',
                        'description': 'Description 2',
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9780987654321'}]
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        # Mock _create_or_get_from_volume to return True (simulating new book created)
        with patch('books.services._create_or_get_from_volume') as mock_create:
            mock_create.return_value = True

            count = import_books_by_author('Test Author')

            print(f"Imported {count} books.")
            assert count == 2
            assert mock_get.called
            assert mock_create.call_count == 2

def test_author_book_refresh_view():
    print("\nTesting AuthorBookRefreshView...")

    # Create a dummy author and user
    author = Author.objects.create(name="Test Author View")
    User = get_user_model()
    try:
        user = User.objects.get(username='testuser')
        user.delete()
    except User.DoesNotExist:
        pass
    user = User.objects.create_user(username='testuser', password='testpassword')

    client = APIClient()
    client.force_authenticate(user=user)

    # Mock import_books_by_author and ALLOWED_HOSTS
    with patch('books.services.import_books_by_author') as mock_import, \
         patch('django.conf.settings.ALLOWED_HOSTS', ['testserver', 'localhost', '127.0.0.1']):
        mock_import.return_value = 5

        response = client.post(f'/api/v1/books/authors/{author.id}/refresh-books/')

        print(f"Response status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Response data: {response.data}")
        else:
             print(f"Response content: {response.content}")

        assert response.status_code == 200
        assert response.data['count'] == 5

    # Clean up
    author.delete()
    user.delete()

if __name__ == "__main__":
    try:
        test_import_books_by_author()
        test_author_book_refresh_view()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
