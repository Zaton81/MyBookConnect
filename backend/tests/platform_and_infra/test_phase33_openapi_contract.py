import pytest
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient
import yaml


@pytest.mark.django_db
class TestPhase33OpenAPIContract:
    """
    Suite de pruebas para validar el contrato OpenAPI 3.0 y la generación de documentación.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

    def test_schema_endpoint_returns_valid_openapi_yaml(self):
        """Verifica que el endpoint /api/schema/ retorne un esquema OpenAPI 3.0 válido en YAML."""
        response = self.client.get('/api/schema/')
        assert response.status_code == status.HTTP_200_OK

        # Parsear YAML
        content = response.content.decode('utf-8')
        data = yaml.safe_load(content)

        assert 'openapi' in data
        assert data['openapi'].startswith('3.0')
        assert 'info' in data
        assert data['info']['title'] == 'MyBookConnect API'
        assert data['info']['version'] == '1.0.0'
        assert 'paths' in data
        assert 'components' in data

    def test_swagger_ui_documentation_renders(self):
        """Verifica que Swagger UI esté disponible en /api/docs/."""
        response = self.client.get('/api/docs/')
        assert response.status_code == status.HTTP_200_OK
        assert 'swagger-ui' in response.content.decode('utf-8').lower()

    def test_redoc_documentation_renders(self):
        """Verifica que Redoc esté disponible en /api/redoc/."""
        response = self.client.get('/api/redoc/')
        assert response.status_code == status.HTTP_200_OK
        assert 'redoc' in response.content.decode('utf-8').lower()

    def test_schema_contains_core_domains_and_paths(self):
        """Verifica que las rutas principales de todos los dominios estén registradas."""
        response = self.client.get('/api/schema/')
        data = yaml.safe_load(response.content.decode('utf-8'))
        paths = data.get('paths', {})

        # Dominios clave ampliados con Fase 31 y 32
        expected_paths = [
            '/api/v1/books/',
            '/api/v1/books/{id}/',
            '/api/v1/books/user/books/',
            '/api/v1/books/trending/',
            '/api/v1/books/statistics/',
            '/api/v1/reviews/',
            '/api/v1/books/reading-lists/',
            '/api/v1/auth/profile/',
            '/api/v1/auth/feed/',
            '/api/v1/books/ai/assistant/',
            '/api/v1/books/ai/status/',
            '/api/v1/auth/messages/',
            '/api/v1/books/authors/',
            '/api/v1/books/authors/claim/',
            '/api/v1/books/authors/dashboard/',
            '/api/v1/books/{id}/affiliate-links/',
        ]

        for expected_path in expected_paths:
            assert expected_path in paths, f"Ruta esperada no encontrada en OpenAPI: {expected_path}"

    def test_schema_contains_typed_components(self):
        """Verifica que los esquemas de entidades centrales existan en components/schemas."""
        response = self.client.get('/api/schema/')
        data = yaml.safe_load(response.content.decode('utf-8'))
        schemas = data.get('components', {}).get('schemas', {})

        # Componentes requeridos
        expected_schemas = [
            'Book',
            'Review',
            'User',
            'UserBasic',
            'ReadingList',
            'ReadingListItem',
            'ReviewComment',
            'ReviewLikeToggleResponse',
            'ReadingStatsResponse',
            'AIStatusResponse',
        ]

        for schema_name in expected_schemas:
            assert schema_name in schemas, f"Esquema no encontrado en components: {schema_name}"

    def test_spectacular_management_command_generates_schema_without_crashing(self, tmp_path):
        """Verifica que el comando de management 'spectacular' genere el esquema a archivo sin errores."""
        target_file = tmp_path / "test_schema.yaml"
        call_command('spectacular', file=str(target_file))
        assert target_file.exists()
        assert target_file.stat().st_size > 10000

    def test_book_api_response_adheres_to_contract(self):
        """Verifica que la respuesta real de /api/v1/books/ cumpla el contrato de campos esenciales."""
        from books.models import Book, Author
        author = Author.objects.create(name="Gabriel García Márquez", biography="Premio Nobel")
        book = Book.objects.create(
            title="Cien años de soledad",
            author=author,
            isbn="9780307474728",
            description="La historia de la familia Buendía en Macondo."
        )
        book.authors.add(author)

        response = self.client.get('/api/v1/books/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'results' in data or isinstance(data, list)
        items = data['results'] if 'results' in data else data
        assert len(items) >= 1

        first_book = next(b for b in items if b['id'] == book.id)
        assert first_book['title'] == "Cien años de soledad"
        assert first_book['author']['name'] == "Gabriel García Márquez"
        assert 'authors' in first_book
        assert isinstance(first_book['authors'], list)
        assert len(first_book['authors']) == 1
        assert first_book['authors'][0]['name'] == "Gabriel García Márquez"

        # Validar contrato del endpoint dedicado de afiliación (Fase 31)
        res_affiliate = self.client.get(f'/api/v1/books/{book.id}/affiliate-links/')
        assert res_affiliate.status_code == status.HTTP_200_OK
        affiliate_data = res_affiliate.json()
        assert affiliate_data.get('affiliate_tag') == 'mybooksocial-21'
        assert 'links' in affiliate_data
        assert 'paperback' in affiliate_data['links']
        assert 'tag=mybooksocial-21' in affiliate_data['links']['paperback']['url']

    def test_user_post_api_response_adheres_to_contract(self):
        """Verifica que la respuesta de /api/v1/users/<id>/posts/ cumpla el contrato de muro social."""
        from django.contrib.auth import get_user_model
        from books.models import Book, Author
        from users.models import UserPost

        User = get_user_model()
        user = User.objects.create_user(username="contract_user", email="contract@example.com", password="Pass123!SafePassword")
        author = Author.objects.create(name="Gabriel García Márquez")
        book = Book.objects.create(title="El amor en los tiempos del cólera", author=author)
        post = UserPost.objects.create(
            author=user,
            target_user=user,
            content="¡Empezando una maravillosa lectura!",
            book=book
        )

        response = self.client.get(f'/api/v1/users/{user.id}/posts/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        items = data['results'] if 'results' in data else data
        assert len(items) >= 1

        first_post = next(p for p in items if p['id'] == post.id)
        assert first_post['id'] == post.id
        assert first_post['content'] == "¡Empezando una maravillosa lectura!"
        assert first_post['author']['id'] == user.id
        assert first_post['author']['username'] == "contract_user"
        assert first_post['book']['id'] == book.id
        assert first_post['book']['title'] == "El amor en los tiempos del cólera"
        assert 'likes_count' in first_post
        assert 'comments_count' in first_post
        assert 'user_has_liked' in first_post

