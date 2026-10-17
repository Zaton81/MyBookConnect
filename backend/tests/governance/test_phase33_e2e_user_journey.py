import pytest
from rest_framework import status
from rest_framework.test import APIClient
from books.models import Book, Author, Category
from users.models import UserPost, UserPostComment


@pytest.mark.django_db
class TestPhase33E2EUserJourney:
    """
    Test E2E de integración que simula el ciclo de vida completo del usuario en MyBookConnect:
    1. Registro y obtención de credenciales JWT
    2. Flujo de onboarding y configuración de preferencias literarias
    3. Búsqueda y selección de libros en el catálogo
    4. Adición del libro a la biblioteca personal (estantería)
    5. Creación de una reseña y calificación
    6. Publicación en el muro social del perfil
    7. Interacción social de un segundo usuario (follow, like en post, comentario y verificación de feed)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client_alice = APIClient()
        self.client_bob = APIClient()

        # Sembrar categorías y catálogo base
        self.cat_fiction = Category.objects.create(name="Ficción", slug="ficcion")
        self.cat_scifi = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")

        self.author_garcia = Author.objects.create(name="Gabriel García Márquez", biography="Premio Nobel de Literatura")
        self.book_macondo = Book.objects.create(
            title="Cien años de soledad",
            author=self.author_garcia,
            isbn="9780307474728",
            description="Historia legendaria de Macondo."
        )
        self.book_macondo.authors.add(self.author_garcia)
        self.book_macondo.categories.add(self.cat_fiction)

    def test_complete_e2e_user_journey(self):
        # ---------------------------------------------------------
        # PASO 1: Registro y autenticación de Alice
        # ---------------------------------------------------------
        register_payload = {
            "username": "alice_reader",
            "email": "alice@example.com",
            "password": "Password123!Secure",
            "password2": "Password123!Secure"
        }
        res_reg = self.client_alice.post("/api/v1/auth/register/", register_payload, format="json")
        assert res_reg.status_code == status.HTTP_201_CREATED, res_reg.data
        from django.contrib.auth import get_user_model
        User = get_user_model()
        alice_user = User.objects.get(username="alice_reader")
        alice_id = alice_user.id

        # Login para obtener tokens JWT
        login_payload = {
            "username": "alice_reader",
            "password": "Password123!Secure"
        }
        res_login = self.client_alice.post("/api/v1/auth/token/", login_payload, format="json")
        assert res_login.status_code == status.HTTP_200_OK, res_login.data
        assert "access" in res_login.data
        alice_token = res_login.data["access"]
        self.client_alice.credentials(HTTP_AUTHORIZATION=f"Bearer {alice_token}")

        # ---------------------------------------------------------
        # PASO 2: Onboarding de Alice (Preferencias de lectura)
        # ---------------------------------------------------------
        onboarding_payload = {
            "favorite_categories": [self.cat_fiction.id, self.cat_scifi.id],
            "reading_goal_books": 25
        }
        res_onboarding = self.client_alice.post("/api/v1/auth/onboarding/complete/", onboarding_payload, format="json")
        assert res_onboarding.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], res_onboarding.data

        # ---------------------------------------------------------
        # PASO 3: Búsqueda y descubrimiento de libro en catálogo
        # ---------------------------------------------------------
        res_search = self.client_alice.get("/api/v1/books/?search=soledad")
        assert res_search.status_code == status.HTTP_200_OK
        results = res_search.data.get("results", res_search.data)
        assert len(results) >= 1
        found_book = next(b for b in results if b["id"] == self.book_macondo.id)
        assert found_book["title"] == "Cien años de soledad"

        # Verificar enlaces de afiliación para monetización
        res_aff = self.client_alice.get(f"/api/v1/books/{found_book['id']}/affiliate-links/")
        assert res_aff.status_code == status.HTTP_200_OK
        assert res_aff.data.get("affiliate_tag") == "mybooksocial-21"
        assert "paperback" in res_aff.data.get("links", {})

        # ---------------------------------------------------------
        # PASO 4: Agregar a biblioteca personal (UserBook - READING)
        # ---------------------------------------------------------
        userbook_payload = {
            "book_id": self.book_macondo.id,
            "status": "reading",
            "current_page": 120
        }
        res_ub = self.client_alice.post("/api/v1/books/user/books/", userbook_payload, format="json")
        assert res_ub.status_code == status.HTTP_201_CREATED, res_ub.data
        assert res_ub.data["status"] == "reading"

        # ---------------------------------------------------------
        # PASO 5: Crear Reseña con Calificación
        # ---------------------------------------------------------
        review_payload = {
            "book_id": self.book_macondo.id,
            "rating": 5,
            "title": "Una obra cumbre imprescindible",
            "text": "Macondo y la familia Buendía quedan grabados en la memoria para siempre."
        }
        res_rev = self.client_alice.post("/api/v1/reviews/", review_payload, format="json")
        assert res_rev.status_code == status.HTTP_201_CREATED, res_rev.data
        review_id = res_rev.data["id"]

        # ---------------------------------------------------------
        # PASO 6: Publicar en el muro social del perfil
        # ---------------------------------------------------------
        post_payload = {
            "content": "¡Acabo de publicar mi reseña de Cien años de soledad! ¿Alguien más lo ha leído?",
            "book_id": self.book_macondo.id
        }
        res_post = self.client_alice.post(f"/api/v1/users/{alice_id}/posts/", post_payload, format="json")
        assert res_post.status_code == status.HTTP_201_CREATED, res_post.data
        post_id = res_post.data["id"]
        assert res_post.data["content"] == post_payload["content"]
        assert res_post.data["author"]["id"] == alice_id
        assert res_post.data["book"]["id"] == self.book_macondo.id

        # ---------------------------------------------------------
        # PASO 7: Interacción de Bob (Registro, Seguir, Like, Comentario y Feed)
        # ---------------------------------------------------------
        # Registro y login de Bob
        self.client_bob.post("/api/v1/auth/register/", {
            "username": "bob_bibliophile",
            "email": "bob@example.com",
            "password": "Password123!Secure",
            "password2": "Password123!Secure"
        }, format="json")
        res_bob_token = self.client_bob.post("/api/v1/auth/token/", {
            "username": "bob_bibliophile",
            "password": "Password123!Secure"
        }, format="json")
        bob_token = res_bob_token.data["access"]
        self.client_bob.credentials(HTTP_AUTHORIZATION=f"Bearer {bob_token}")

        # Bob sigue a Alice
        res_follow = self.client_bob.post(f"/api/v1/users/{alice_id}/follow/")
        assert res_follow.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED], res_follow.data

        # Bob consulta el muro de Alice
        res_alice_wall = self.client_bob.get(f"/api/v1/users/{alice_id}/posts/")
        assert res_alice_wall.status_code == status.HTTP_200_OK
        wall_posts = res_alice_wall.data if isinstance(res_alice_wall.data, list) else res_alice_wall.data.get("results", [])
        assert len(wall_posts) >= 1
        assert wall_posts[0]["id"] == post_id

        # Bob da like al post de Alice
        res_like = self.client_bob.post(f"/api/v1/users/posts/{post_id}/like/")
        assert res_like.status_code == status.HTTP_200_OK
        assert res_like.data["liked"] is True
        assert res_like.data["likes_count"] == 1

        # Bob comenta en el post de Alice (usando campo text sanitizado)
        comment_payload = {
            "text": "¡Totalmente de acuerdo Alice, una de las mejores novelas del siglo XX!"
        }
        res_comment = self.client_bob.post(f"/api/v1/users/posts/{post_id}/comments/", comment_payload, format="json")
        assert res_comment.status_code == status.HTTP_201_CREATED, res_comment.data
        assert res_comment.data["text"] == comment_payload["text"]
        assert res_comment.data["user"]["username"] == "bob_bibliophile"

        # Bob consulta el feed social
        res_feed = self.client_bob.get("/api/v1/auth/feed/")
        assert res_feed.status_code == status.HTTP_200_OK
        feed_data = res_feed.data if isinstance(res_feed.data, list) else res_feed.data.get("results", [])
        assert len(feed_data) >= 1
        alice_activities = [act for act in feed_data if act.get("user", {}).get("username") == "alice_reader"]
        assert len(alice_activities) >= 1
