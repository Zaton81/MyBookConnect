"""
Suite de Pruebas Automatizadas para el Sprint 20: IA Multimodal y Asistente Literario Ampliado.
RoadmapV3 Sección 30 (IA Multimodal).
Verifica visión multimodal de portadas, extracción de paletas cromáticas, estilo artístico,
descripciones accesibles (WCAG alt text), chat multimodal y observabilidad en AIUsageLog.
"""
import base64
import io
import pytest
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from ai.models import AIUsageLog
from books.models import Author, Book

User = get_user_model()


def _generate_test_image_bytes(color=(30, 41, 59), size=(200, 300)) -> bytes:
    """Genera bytes reales de una imagen PNG para pruebas."""
    img = Image.new('RGB', size, color=color)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def reader_user(db):
    return User.objects.create_user(
        username="lectora_multimodal",
        email="lectora@example.com",
        password="Password123!",
    )


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Brandon Sanderson", is_verified=True)
    img_bytes = _generate_test_image_bytes(color=(15, 118, 110))
    uploaded_cover = SimpleUploadedFile(
        name="mistborn_cover.png",
        content=img_bytes,
        content_type="image/png",
    )
    return Book.objects.create(
        title="Nacidos de la Bruma: El Imperio Final",
        author=author,
        cover=uploaded_cover,
        description="Fantasía épica y sistema de magia alomántica.",
    )


@pytest.mark.django_db
class TestSprint20MultimodalAI:
    def test_analyze_cover_image_valid_base64(self, api_client, reader_user, sample_book):
        """
        Verifica que POST /api/v1/books/ai/multimodal/analyze-cover/ procesa una imagen en base64,
        extrae paleta cromática, estilo artístico, atmósfera y descripción accesible (alt text).
        """
        api_client.force_authenticate(user=reader_user)

        img_bytes = _generate_test_image_bytes(color=(99, 102, 241), size=(250, 380))
        b64_str = base64.b64encode(img_bytes).decode('utf-8')
        payload = {
            "image_base64": f"data:image/png;base64,{b64_str}",
            "book_id": sample_book.id,
        }

        response = api_client.post(
            "/api/v1/books/ai/multimodal/analyze-cover/",
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["status"] == "success"
        assert data["is_ai_generated"] is True
        assert "✨" in data["badge"]
        assert len(data["color_palette"]) >= 2
        assert "hex" in data["color_palette"][0]
        assert "name" in data["color_palette"][0]
        assert data["art_style"] != ""
        assert data["mood_atmosphere"] != ""
        assert "Nacidos de la Bruma" in data["accessible_alt_text"]
        assert data["matching_book"]["id"] == sample_book.id

    def test_analyze_cover_image_with_uploaded_file(self, api_client, reader_user):
        """
        Verifica que el endpoint acepta un archivo de imagen real mediante multipart/form-data.
        """
        api_client.force_authenticate(user=reader_user)

        img_bytes = _generate_test_image_bytes(color=(217, 119, 6), size=(180, 260))
        uploaded_file = SimpleUploadedFile(
            name="test_book_cover.png",
            content=img_bytes,
            content_type="image/png",
        )

        response = api_client.post(
            "/api/v1/books/ai/multimodal/analyze-cover/",
            {"image": uploaded_file},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["dimensions"]["width"] == 180
        assert data["dimensions"]["height"] == 260
        assert len(data["color_palette"]) > 0

    def test_analyze_cover_missing_image_payload(self, api_client, reader_user):
        """
        Verifica que se retorna 400 Bad Request si la petición carece del parámetro 'image'.
        """
        api_client.force_authenticate(user=reader_user)
        response = api_client.post(
            "/api/v1/books/ai/multimodal/analyze-cover/",
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Se requiere una imagen" in response.data["detail"]

    def test_multimodal_assistant_chat_with_image(self, api_client, reader_user, sample_book):
        """
        Verifica que POST /api/v1/books/ai/multimodal/assistant/ procesa un mensaje conversacional
        con una imagen adjunta, responde con análisis estético y registra el consumo en AIUsageLog.
        """
        api_client.force_authenticate(user=reader_user)

        img_bytes = _generate_test_image_bytes(color=(16, 185, 129))
        b64_str = base64.b64encode(img_bytes).decode('utf-8')

        payload = {
            "messages": [
                {"role": "user", "content": "¿Qué te transmite el diseño y estilo de esta portada?"}
            ],
            "image_base64": b64_str,
            "book_id": sample_book.id,
        }

        response = api_client.post(
            "/api/v1/books/ai/multimodal/assistant/",
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["is_ai_generated"] is True
        assert data["has_image_attached"] is True
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert "Estilo visual detectado" in data["message"]["content"]
        assert "Paleta cromática" in data["message"]["content"]

        # Verificar observabilidad en AIUsageLog
        log_entry = AIUsageLog.objects.filter(user=reader_user, provider="multimodal_assistant").first()
        assert log_entry is not None
        assert log_entry.success is True

    def test_multimodal_assistant_chat_text_only(self, api_client, reader_user, sample_book):
        """
        Verifica que el asistente multimodal opera correctamente también cuando no se adjunta imagen.
        """
        api_client.force_authenticate(user=reader_user)

        payload = {
            "messages": [
                {"role": "user", "content": "¿Es una buena novela para comenzar con Sanderson?"}
            ],
            "book_id": sample_book.id,
        }

        response = api_client.post(
            "/api/v1/books/ai/multimodal/assistant/",
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["has_image_attached"] is False
        assert response.data["message"]["role"] == "assistant"

    def test_book_visual_insights_endpoint(self, api_client, reader_user, sample_book):
        """
        Verifica que GET /api/v1/books/<id>/ai/visual-insights/ retorna los insights
        estéticos y cromáticos consolidados para una obra catalogada.
        """
        api_client.force_authenticate(user=reader_user)

        response = api_client.get(f"/api/v1/books/{sample_book.id}/ai/visual-insights/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["book_id"] == sample_book.id
        assert data["book_title"] == "Nacidos de la Bruma: El Imperio Final"
        assert len(data["color_palette"]) >= 2
        assert "art_style" in data
        assert "accessible_alt_text" in data
        assert "✨" in data["badge"]

    def test_multimodal_endpoints_require_authentication(self, api_client):
        """
        Verifica que los endpoints multimodales exigen autenticación (401 si es anónimo).
        """
        resp_cover = api_client.post("/api/v1/books/ai/multimodal/analyze-cover/", {})
        assert resp_cover.status_code == status.HTTP_401_UNAUTHORIZED

        resp_chat = api_client.post("/api/v1/books/ai/multimodal/assistant/", {})
        assert resp_chat.status_code == status.HTTP_401_UNAUTHORIZED
