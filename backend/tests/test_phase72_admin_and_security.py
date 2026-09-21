import io

import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from books.admin import AuthorAdmin, BookAdmin, CategoryAdmin
from books.models import Author, Book
from mybookconnect.media_security import validate_image_file

User = get_user_model()


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username='test_admin_sec',
        email='secadmin@example.com',
        password='StrongPassword123!',
    )


@pytest.fixture
def sample_image():
    f = io.BytesIO()
    img = Image.new('RGB', (120, 160), color='forestgreen')
    img.save(f, format='JPEG')
    f.seek(0)
    return SimpleUploadedFile('sample.jpg', f.read(), content_type='image/jpeg')


@pytest.fixture
def sample_png():
    f = io.BytesIO()
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
    img.save(f, format='PNG')
    f.seek(0)
    return SimpleUploadedFile('sample.png', f.read(), content_type='image/x-png')


class TestPhase72AdminAndSecurity:
    """
    Suite de pruebas para la Fase 72:
    - Ruta ofuscada y configurable del panel de administración
    - Trampa de seguridad (señuelo) en /admin/
    - Carga y previsualización de portadas y fotografías en BookAdmin y AuthorAdmin
    - Selección fluida de autores y géneros vía autocompletado en BookAdmin
    - Soporte de archivos estáticos para Select2 y estilos en el servidor
    - Tolerancia de tipos MIME extendidos en media_security
    """

    def test_admin_url_is_obfuscated_and_configurable(self):
        """Verifica que ADMIN_URL esté configurada con una ruta ofuscada distinta a 'admin/'."""
        assert hasattr(settings, 'ADMIN_URL')
        admin_url = settings.ADMIN_URL.strip('/')
        assert admin_url != 'admin', "La ruta del admin no debe ser la ruta predeterminada 'admin/'."
        assert len(admin_url) >= 8, "La ruta ofuscada debe tener suficiente entropía."

        # Verificar resolución de URL reversa
        index_url = reverse('admin:index')
        assert index_url.startswith(f"/{admin_url}/")

    def test_admin_probe_trap_returns_404(self, client):
        """Verifica que peticiones a la ruta antigua /admin/ caigan en el señuelo y devuelvan 404."""
        response = client.get('/admin/', HTTP_HOST='localhost')
        assert response.status_code == 404
        assert "Página no encontrada." in response.content.decode()

    def test_obfuscated_admin_index_accessible_to_superuser(self, client, superuser):
        """Verifica que el superusuario acceda correctamente a la nueva ruta ofuscada."""
        client.force_login(superuser)
        admin_url = f"/{settings.ADMIN_URL}"
        response = client.get(admin_url, HTTP_HOST='localhost')
        assert response.status_code == 200
        content = response.content.decode()
        assert "Administración de Django" in content or "Site administration" in content

    def test_author_admin_photo_upload_and_preview(self, db, sample_image):
        """Verifica que AuthorAdmin genere previsualización HTML de la fotografía y maneje autores sin foto."""
        author = Author.objects.create(name="Virginia Woolf", photo=sample_image)
        author_admin = AuthorAdmin(Author, admin.site)

        # Previsualización con foto
        preview_html = author_admin.photo_preview(author)
        assert "<img" in preview_html
        assert author.photo.url in preview_html
        assert "Virginia Woolf" in preview_html

        # Previsualización sin foto
        author_sin_foto = Author.objects.create(name="Autor Desconocido")
        preview_vacio = author_admin.photo_preview(author_sin_foto)
        assert "Sin foto" in preview_vacio

    def test_book_admin_cover_upload_and_preview(self, db, sample_image):
        """Verifica que BookAdmin genere previsualización HTML de la portada y maneje libros sin portada."""
        author = Author.objects.create(name="George Orwell")
        book = Book.objects.create(title="1984", author=author, cover=sample_image)
        book_admin = BookAdmin(Book, admin.site)

        # Previsualización con portada
        preview_html = book_admin.cover_preview(book)
        assert "<img" in preview_html
        assert book.cover.url in preview_html
        assert "1984" in preview_html

        # Previsualización sin portada
        book_sin_portada = Book.objects.create(title="Libro Anónimo")
        preview_vacio = book_admin.cover_preview(book_sin_portada)
        assert "Sin portada" in preview_vacio

    def test_book_admin_autocomplete_fields_configuration(self):
        """Verifica que BookAdmin declare author y categories en autocomplete_fields y los modelos relacionados tengan search_fields."""
        assert 'author' in BookAdmin.autocomplete_fields
        assert 'categories' in BookAdmin.autocomplete_fields

        # Para que autocomplete funcione en Django, los modelos relacionados deben tener search_fields
        assert AuthorAdmin.search_fields, "AuthorAdmin debe declarar search_fields para soportar autocompletado."
        assert CategoryAdmin.search_fields, "CategoryAdmin debe declarar search_fields para soportar autocompletado."

    def test_media_security_accepts_pjpeg_and_x_png(self, sample_image, sample_png):
        """Verifica que el validador multimedia acepte formatos de compatibilidad MIME como image/pjpeg e image/x-png."""
        # Probar image/pjpeg
        sample_image.content_type = 'image/pjpeg'
        validate_image_file(sample_image, max_size_bytes=10 * 1024 * 1024)

        # Probar image/x-png
        sample_png.content_type = 'image/x-png'
        validate_image_file(sample_png, max_size_bytes=10 * 1024 * 1024)

        # Probar fallback ante application/octet-stream con bytes válidos
        sample_image.content_type = 'application/octet-stream'
        validate_image_file(sample_image, max_size_bytes=10 * 1024 * 1024)

    def test_book_admin_fieldsets_structure(self):
        """Verifica que BookAdmin y AuthorAdmin tengan fieldsets definidos y organizados."""
        fieldsets = dict(BookAdmin.fieldsets)
        assert "Información Principal" in fieldsets
        assert "Portada del Libro" in fieldsets

        author_fieldsets = dict(AuthorAdmin.fieldsets)
        assert "Datos del Autor" in author_fieldsets
        assert "Fotografía del Autor" in author_fieldsets

    def test_admin_category_api_all_and_create(self, superuser):
        """Verifica que el endpoint de categorías permita crear categorías sin slug y listarlas todas con ?all=true."""
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=superuser)

        # Crear categoría sin slug
        res = api_client.post(
            '/api/v1/admin/categories/',
            data={'name': 'Afrofuturismo Literario'},
            format='json',
        )
        assert res.status_code == 201
        data = res.json()
        assert data['name'] == 'Afrofuturismo Literario'
        assert data['slug'] == 'afrofuturismo-literario'

        # Listar todas las categorías sin paginación con ?all=true
        res_list = api_client.get('/api/v1/admin/categories/?all=true')
        assert res_list.status_code == 200
        cats = res_list.json()
        assert isinstance(cats, list), "Con ?all=true debe retornar una lista sin formato paginado {results: [...]}."
        assert any(c['name'] == 'Afrofuturismo Literario' for c in cats)

    def test_admin_author_api_all(self, superuser):
        """Verifica que el endpoint de autores soporte ?all=true."""
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=superuser)

        Author.objects.create(name="Octavia E. Butler")
        res = api_client.get('/api/v1/admin/authors/?all=true')
        assert res.status_code == 200
        authors = res.json()
        assert isinstance(authors, list)
        assert any(a['name'] == 'Octavia E. Butler' for a in authors)

    def test_admin_book_create_api_with_cover(self, superuser, sample_image):
        """Verifica la creación de un libro a través del endpoint admin con portada multipart y géneros."""
        from rest_framework.test import APIClient
        api_client = APIClient()
        api_client.force_authenticate(user=superuser)

        author = Author.objects.create(name="Ursula K. Le Guin")
        res = api_client.post(
            '/api/v1/admin/categories/',
            data={'name': 'Fantasía Filosófica'},
            format='json',
        )
        cat_id = res.json()['id']

        # Enviar POST multipart/form-data
        post_data = {
            'title': 'Un mago de Terramar',
            'author_id': author.id,
            'category_ids': [cat_id],
            'cover': sample_image,
        }
        res_book = api_client.post('/api/v1/admin/books/', data=post_data, format='multipart')
        assert res_book.status_code == 201
        book_data = res_book.json()
        assert book_data['title'] == 'Un mago de Terramar'
        assert book_data['author']['id'] == author.id
        assert any(c['id'] == cat_id for c in book_data['categories'])
        assert book_data['cover'] is not None

