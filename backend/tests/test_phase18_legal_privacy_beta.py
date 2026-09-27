import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient

from books.models import LegalDocument

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="adminlegal",
        email="adminlegal@example.com",
        password="AdminLegalPassword123!",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="readeruser",
        email="reader@example.com",
        password="ReaderPassword123!",
    )


@pytest.mark.django_db
class TestPhase18LegalAndPrivacyBeta:
    def test_seed_legal_documents_command(self):
        """Verifica que el comando seed_legal_documents crea los 7 documentos normativos."""
        call_command('seed_legal_documents')
        
        expected_slugs = {
            'terms',
            'privacy',
            'cookies',
            'legal_notice',
            'content_policy',
            'deletion_policy',
            'contact',
        }
        
        docs = LegalDocument.objects.filter(slug__in=expected_slugs)
        assert docs.count() == 7
        found_slugs = set(docs.values_list('slug', flat=True))
        assert found_slugs == expected_slugs

    def test_public_legal_document_list(self, api_client):
        """Verifica que el endpoint GET /api/v1/books/legal/ lista todos los documentos públicos."""
        call_command('seed_legal_documents')
        
        url = "/api/v1/books/legal/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # Debe devolver una lista con al menos los 7 documentos
        data = response.data
        assert isinstance(data, list)
        assert len(data) >= 7
        
        slugs = [item['slug'] for item in data]
        assert 'privacy' in slugs
        assert 'terms' in slugs
        assert 'cookies' in slugs
        assert 'legal_notice' in slugs
        assert 'content_policy' in slugs
        assert 'deletion_policy' in slugs
        assert 'contact' in slugs

    def test_public_legal_document_detail_contents(self, api_client):
        """Verifica que cada documento público es accesible y contiene las secciones requeridas."""
        call_command('seed_legal_documents')
        
        # 1. Política de Privacidad
        r_priv = api_client.get("/api/v1/books/legal/privacy/")
        assert r_priv.status_code == status.HTTP_200_OK
        content_priv = r_priv.data['content']
        assert "RGPD" in content_priv or "Reglamento General" in content_priv
        assert "Proveedores" in content_priv or "proveedores" in content_priv
        assert "Inteligencia Artificial" in content_priv
        assert "entrenar" in content_priv.lower()
        assert "Analytics" in content_priv or "analytics" in content_priv
        assert "Retención" in content_priv or "retención" in content_priv

        # 2. Términos de Servicio
        r_terms = api_client.get("/api/v1/books/legal/terms/")
        assert r_terms.status_code == status.HTTP_200_OK
        assert "Beta" in r_terms.data['content']

        # 3. Política de Cookies
        r_cookies = api_client.get("/api/v1/books/legal/cookies/")
        assert r_cookies.status_code == status.HTTP_200_OK
        assert "JWT" in r_cookies.data['content'] or "técnicas" in r_cookies.data['content'].lower()

        # 4. Aviso Legal
        r_notice = api_client.get("/api/v1/books/legal/legal_notice/")
        assert r_notice.status_code == status.HTTP_200_OK
        assert "LSSI" in r_notice.data['content']

        # 5. Política de Contenido
        r_content = api_client.get("/api/v1/books/legal/content_policy/")
        assert r_content.status_code == status.HTTP_200_OK
        assert "Comunidad" in r_content.data['content']

        # 6. Política de Eliminación
        r_del = api_client.get("/api/v1/books/legal/deletion_policy/")
        assert r_del.status_code == status.HTTP_200_OK
        assert "Artículo 17" in r_del.data['content'] or "Derecho al Olvido" in r_del.data['content']

        # 7. Contacto
        r_contact = api_client.get("/api/v1/books/legal/contact/")
        assert r_contact.status_code == status.HTTP_200_OK
        assert "privacidad@mybookconnect.local" in r_contact.data['content']

    def test_public_legal_document_not_found(self, api_client):
        """Verifica que un slug inexistente devuelve 404."""
        response = api_client.get("/api/v1/books/legal/invaliddoc/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_anonymous_and_regular_user_cannot_modify_legal_documents(self, api_client, regular_user):
        """Verifica que ni usuarios anónimos ni usuarios estándar pueden modificar documentos legales."""
        call_command('seed_legal_documents')
        
        # En la API pública sólo se admiten métodos de lectura segura
        post_pub = api_client.post("/api/v1/books/legal/", {"title": "Hack"}, format="json")
        assert post_pub.status_code in (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        
        put_pub = api_client.put("/api/v1/books/legal/terms/", {"title": "Hack"}, format="json")
        assert put_pub.status_code in (status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

        # En la API de administración, usuario anónimo recibe 401
        put_admin = api_client.put("/api/v1/admin/legal/terms/", {"title": "Hack"}, format="json")
        assert put_admin.status_code == status.HTTP_401_UNAUTHORIZED

        # Usuario autenticado normal recibe 403 Forbidden en admin endpoint
        api_client.force_authenticate(user=regular_user)
        put_admin_user = api_client.put("/api/v1/admin/legal/terms/", {"title": "Hack"}, format="json")
        assert put_admin_user.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_update_legal_document(self, api_client, superuser):
        """Verifica que un administrador puede actualizar el contenido de un documento legal."""
        call_command('seed_legal_documents')
        api_client.force_authenticate(user=superuser)

        url = "/api/v1/admin/legal/terms/"
        payload = {
            "slug": "terms",
            "title": "Términos Actualizados por Admin",
            "content": "Nuevo texto de términos y condiciones para la beta.",
        }

        response = api_client.put(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Términos Actualizados por Admin"

        # Verificar reflejo en la API pública
        api_client.force_authenticate(user=None)
        pub_response = api_client.get("/api/v1/books/legal/terms/")
        assert pub_response.status_code == status.HTTP_200_OK
        assert pub_response.data["title"] == "Términos Actualizados por Admin"
        assert pub_response.data["content"] == "Nuevo texto de términos y condiciones para la beta."
