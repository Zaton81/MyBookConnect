import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from books.models import Book, Author, Review, UserBook
from users.models import UserPost, UserPostComment

User = get_user_model()


@pytest.mark.django_db
class TestPhase33SecurityHardening:
    """
    Suite de verificación de seguridad y resiliencia para la Fase 33:
    - Protección IDOR en posts de muro, comentarios, reseñas y estanterías
    - Manejo seguro de payloads XSS / inyección en contenido generado por usuarios
    - Validación rigurosa de JWT (firma inválida, blacklist tras logout)
    - Respeto estricto de barreras de privacidad (cuentas privadas y bloqueos de usuario)
    - Acceso no autenticado (401 Unauthorized) en endpoints mutables
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client_alice = APIClient()
        self.client_bob = APIClient()
        self.client_anon = APIClient()

        # Crear usuarios Alice y Bob
        self.alice = User.objects.create_user(
            username="alice_sec",
            email="alice_sec@example.com",
            password="SecurePass123!Alice"
        )
        self.bob = User.objects.create_user(
            username="bob_sec",
            email="bob_sec@example.com",
            password="SecurePass123!Bob"
        )

        from django.core.cache import cache
        from rest_framework_simplejwt.tokens import RefreshToken
        cache.clear()

        # Generar tokens JWT para Alice
        alice_refresh_obj = RefreshToken.for_user(self.alice)
        self.alice_token = str(alice_refresh_obj.access_token)
        self.alice_refresh = str(alice_refresh_obj)
        self.client_alice.credentials(HTTP_AUTHORIZATION=f"Bearer {self.alice_token}")

        # Generar tokens JWT para Bob
        bob_refresh_obj = RefreshToken.for_user(self.bob)
        self.bob_token = str(bob_refresh_obj.access_token)
        self.bob_refresh = str(bob_refresh_obj)
        self.client_bob.credentials(HTTP_AUTHORIZATION=f"Bearer {self.bob_token}")

        # Libro de prueba
        self.author = Author.objects.create(name="Alan Turing")
        self.book = Book.objects.create(title="Seguridad en Sistemas Web", author=self.author)

    def test_idor_prevent_delete_other_user_post(self):
        """Un usuario atacante (Bob) no debe poder eliminar una publicación de muro creada por Alice."""
        alice_post = UserPost.objects.create(
            author=self.alice,
            target_user=self.alice,
            content="Post privado de Alice sobre criptografía",
            book=self.book
        )

        # Bob intenta eliminar el post de Alice
        res = self.client_bob.delete(f"/api/v1/users/posts/{alice_post.id}/")
        assert res.status_code == status.HTTP_403_FORBIDDEN, (
            f"Esperado 403 Forbidden para IDOR en UserPost, pero se recibió {res.status_code}"
        )
        assert UserPost.objects.filter(id=alice_post.id).exists()

    def test_idor_prevent_modify_other_user_review(self):
        """Un usuario (Bob) no puede modificar ni borrar la reseña de otro usuario (Alice)."""
        alice_review = Review.objects.create(
            user=self.alice,
            book=self.book,
            rating=5,
            title="Excelente libro",
            text="Muy recomendado para aprender ciberseguridad."
        )

        # Bob intenta modificar la reseña de Alice
        res = self.client_bob.patch(f"/api/v1/reviews/{alice_review.id}/", {
            "rating": 1,
            "title": "Hackeado por Bob"
        }, format="json")
        assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        alice_review.refresh_from_db()
        assert alice_review.rating == 5
        assert alice_review.title == "Excelente libro"

    def test_idor_prevent_modify_other_user_book(self):
        """Un usuario (Bob) no puede modificar el estado de lectura (UserBook) de Alice."""
        alice_ub = UserBook.objects.create(
            user=self.alice,
            book=self.book,
            status="READING",
            current_page=50
        )

        res = self.client_bob.patch(f"/api/v1/books/user/books/{alice_ub.id}/", {
            "current_page": 999
        }, format="json")
        assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
        alice_ub.refresh_from_db()
        assert alice_ub.current_page == 50

    def test_xss_sanitization_in_user_post_and_comment(self):
        """Verifica que payloads maliciosos de script no provoquen vulnerabilidades XSS en posts o comentarios."""
        xss_payload = "<script>alert('XSS_ATTACK')</script><b>Texto Seguro</b>"
        
        # Publicar post con payload
        res_post = self.client_alice.post(f"/api/v1/users/{self.alice.id}/posts/", {
            "content": xss_payload,
            "book_id": self.book.id
        }, format="json")
        assert res_post.status_code == status.HTTP_201_CREATED
        post_id = res_post.data["id"]

        # Comentar con payload malicioso: el sanitizador del backend debe limpiar tags peligrosos
        res_comment = self.client_bob.post(f"/api/v1/users/posts/{post_id}/comments/", {
            "text": "<img src=x onerror=alert('PWNED')>Comentario seguro"
        }, format="json")
        assert res_comment.status_code == status.HTTP_201_CREATED
        # El sanitizador extrae texto plano y elimina tags <img ...>
        assert "<img" not in res_comment.data["text"]
        assert "onerror" not in res_comment.data["text"]

        # Al consultar el muro, el contenido se devuelve estructurado y seguro
        res_get = self.client_anon.get(f"/api/v1/users/{self.alice.id}/posts/")
        assert res_get.status_code == status.HTTP_200_OK
        assert "application/json" in res_get["Content-Type"]

    def test_jwt_tampered_or_invalid_token_returns_401(self):
        """Una petición con firma JWT inválida o manipulada debe retornar 401 Unauthorized."""
        tampered_token = self.alice_token[:-10] + "malicious99"
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered_token}")

        res = client.get("/api/v1/auth/profile/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_logout_blacklist_prevents_subsequent_access(self):
        """Tras hacer logout, el token de refresco no puede ser reutilizado para renovar tokens."""
        # Logout
        res_logout = self.client_alice.post("/api/v1/auth/logout/", {
            "refresh": self.alice_refresh
        }, format="json")
        assert res_logout.status_code in [status.HTTP_200_OK, status.HTTP_205_RESET_CONTENT]

        # Intentar refrescar con el token en lista negra
        res_refresh = self.client_alice.post("/api/v1/auth/token/refresh/", {
            "refresh": self.alice_refresh
        }, format="json")
        assert res_refresh.status_code == status.HTTP_401_UNAUTHORIZED

    def test_privacy_boundaries_blocked_user_cannot_view_wall(self):
        """Si Alice bloquea a Bob, Bob no puede ver los posts de muro de Alice (debe devolver 404 o 403)."""
        # Crear post de Alice
        UserPost.objects.create(author=self.alice, target_user=self.alice, content="Pensamiento sobre literatura")

        # Alice bloquea a Bob
        res_block = self.client_alice.post(f"/api/v1/users/{self.bob.id}/block/")
        assert res_block.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]

        # Bob intenta ver el muro de Alice
        res_wall = self.client_bob.get(f"/api/v1/users/{self.alice.id}/posts/")
        assert res_wall.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_unauthenticated_request_to_mutable_endpoints_returns_401(self):
        """Peticiones sin autenticación a creación de posts, likes o comentarios deben retornar 401."""
        post = UserPost.objects.create(author=self.alice, target_user=self.alice, content="Post de prueba")

        # Intentar crear post
        res1 = self.client_anon.post(f"/api/v1/users/{self.alice.id}/posts/", {"content": "Anónimo"})
        assert res1.status_code == status.HTTP_401_UNAUTHORIZED

        # Intentar dar like
        res2 = self.client_anon.post(f"/api/v1/users/posts/{post.id}/like/")
        assert res2.status_code == status.HTTP_401_UNAUTHORIZED

        # Intentar comentar
        res3 = self.client_anon.post(f"/api/v1/users/posts/{post.id}/comments/", {"text": "Comentario anónimo"})
        assert res3.status_code == status.HTTP_401_UNAUTHORIZED
