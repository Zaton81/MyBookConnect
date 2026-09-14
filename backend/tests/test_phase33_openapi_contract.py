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

        # Dominios clave
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
