import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Author, Book, Review, UserBook
from users.models import Activity, ActivityType, Report, ReportReason, ReportStatus, UserPost

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="lector_disciplinado",
        email="lector@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otro_lector",
        email="otro@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_supremo",
        email="admin@example.com",
        password="AdminPassword123!",
    )


@pytest.mark.django_db
class TestSprint7AdminAndModeration:
    """
    Suite de pruebas de integración para las Secciones 24 y 25 de RoadmapV3:
    Administración, Moderación de Contenido, Sistema de Reportes Universal y Fusión de Catálogo.
    """

    def test_report_creation_for_book_author_and_post(self, api_client, regular_user, other_user):
        """1. Reportes sobre Book, Author y UserPost con prevención de auto-denuncias."""
        refresh = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        author = Author.objects.create(name="Autor Problemático", biography="Biografía sospechosa")
        book = Book.objects.create(title="Libro con Contenido Ofensivo", author=author, isbn="9780000000001")
        post = UserPost.objects.create(author=other_user, target_user=other_user, content="Texto con spam masivo")
        my_post = UserPost.objects.create(author=regular_user, target_user=regular_user, content="Mi post propio")

        # a) Reportar libro ajeno
        res_book = api_client.post(
            "/api/v1/reports/",
            {
                "target_type": "book",
                "object_id": book.id,
                "reason": ReportReason.INAPPROPRIATE,
                "description": "Portada o título viola normas de la comunidad.",
            },
            format="json",
        )
        assert res_book.status_code == status.HTTP_201_CREATED
        assert res_book.json()["status"] == ReportStatus.OPEN

        # b) Reportar autor ajeno
        res_author = api_client.post(
            "/api/v1/reports/",
            {
                "target_type": "author",
                "object_id": author.id,
                "reason": ReportReason.IMPERSONATION,
                "description": "Suplantación de identidad de un autor conocido.",
            },
            format="json",
        )
        assert res_author.status_code == status.HTTP_201_CREATED

        # c) Reportar post de otro usuario
        res_post = api_client.post(
            "/api/v1/reports/",
            {
                "target_type": "post",
                "object_id": post.id,
                "reason": ReportReason.SPAM,
                "description": "Enlaces comerciales repetitivos.",
            },
            format="json",
        )
        assert res_post.status_code == status.HTTP_201_CREATED

        # d) Prohibir auto-denuncia sobre post propio
        res_self = api_client.post(
            "/api/v1/reports/",
            {
                "target_type": "post",
                "object_id": my_post.id,
                "reason": ReportReason.SPAM,
                "description": "Auto-reporte ilegal.",
            },
            format="json",
        )
        assert res_self.status_code == status.HTTP_400_BAD_REQUEST

        # e) Prohibir reporte duplicado pendiente sobre el mismo post
        res_dup = api_client.post(
            "/api/v1/reports/",
            {
                "target_type": "post",
                "object_id": post.id,
                "reason": ReportReason.SPAM,
                "description": "Denuncia duplicada.",
            },
            format="json",
        )
        assert res_dup.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_reports_list_previews_and_resolution(self, api_client, admin_user, regular_user, other_user):
        """2. Listado de denuncias con previews enriquecidos y resolución disciplinaria."""
        author = Author.objects.create(name="Escritor Reportado", biography="Bio corta")
        book = Book.objects.create(title="Libro Denunciado", author=author, isbn="9781111111111")
        post = UserPost.objects.create(author=other_user, target_user=other_user, content="Spam abusivo a ocultar")

        # Crear reportes
        report_post = Report.objects.create(
            reporter=regular_user,
            content_object=post,
            reason=ReportReason.SPAM,
            description="Contenido spam comprobado",
        )

        # Autenticar como administrador
        refresh_admin = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")

        # Comprobar listado de denuncias
        res_list = api_client.get("/api/v1/admin/reports/")
        assert res_list.status_code == status.HTTP_200_OK
        results = res_list.json()
        items = results if isinstance(results, list) else results.get("results", [])
        post_item = next(item for item in items if item["id"] == report_post.id)
        assert post_item["target_type"] == "post"
        assert "Spam abusivo" in post_item["target_preview"]["snippet"]

        # Resolver denuncia aplicando HIDE_CONTENT
        res_resolve = api_client.patch(
            f"/api/v1/admin/reports/{report_post.id}/",
            {
                "status": "RESOLVED",
                "action_taken": "HIDE_CONTENT",
                "resolution_notes": "Post eliminado conforme a directrices comunitarias.",
            },
            format="json",
        )
        assert res_resolve.status_code == status.HTTP_200_OK
        assert res_resolve.json()["status"] == ReportStatus.RESOLVED

        # Comprobar que el UserPost fue eliminado del sistema
        assert not UserPost.objects.filter(id=post.id).exists()

    def test_admin_book_merge_endpoint(self, api_client, admin_user, regular_user):
        """3. Fusión administrativa atómica de libros duplicados."""
        author = Author.objects.create(name="Gabriel García Márquez")
        canonical_book = Book.objects.create(
            title="Cien años de soledad",
            author=author,
            isbn="9780307474728",
            description="Edición canónica completa.",
        )
        dup_book1 = Book.objects.create(
            title="Cien anos de soledad (Digital)",
            author=author,
            isbn="9788497592208",
            description="Edición Kindle.",
        )
        dup_book2 = Book.objects.create(
            title="Cien años de soledad - Bolsillo",
            author=author,
            isbn="9788420471839",
        )

        # Lectura y reseña asociadas al duplicado
        UserBook.objects.create(user=regular_user, book=dup_book1, status="completed", current_page=450)
        Review.objects.create(user=regular_user, book=dup_book2, rating=5, text="Obra maestra universal.")

        # Acceso denegado para usuario no staff
        refresh_user = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_user.access_token}")
        res_forbidden = api_client.post(
            "/api/v1/admin/books/merge/",
            {"canonical_id": canonical_book.id, "duplicate_ids": [dup_book1.id, dup_book2.id]},
            format="json",
        )
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # Acceso permitido para admin
        refresh_admin = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")
        res_merge = api_client.post(
            "/api/v1/admin/books/merge/",
            {"canonical_id": canonical_book.id, "duplicate_ids": [dup_book1.id, dup_book2.id]},
            format="json",
        )
        assert res_merge.status_code == status.HTTP_200_OK

        # Verificar que los duplicados ya no existen y el canónico absorbió dependencias
        assert not Book.objects.filter(id__in=[dup_book1.id, dup_book2.id]).exists()
        canonical_book.refresh_from_db()
        assert "9788497592208" in canonical_book.additional_isbns
        assert "9788420471839" in canonical_book.additional_isbns
        assert UserBook.objects.filter(book=canonical_book, user=regular_user).exists()
        assert Review.objects.filter(book=canonical_book, user=regular_user).exists()

    def test_admin_author_merge_endpoint(self, api_client, admin_user):
        """4. Fusión administrativa atómica de autores duplicados."""
        canonical_author = Author.objects.create(name="Isaac Asimov", biography="Escritor y bioquímico prolífico.")
        dup_author = Author.objects.create(name="I. Asimov", biography="Autor de ciencia ficción.")

        b1 = Book.objects.create(title="Fundación", author=canonical_author)
        b2 = Book.objects.create(title="Yo, Robot", author=dup_author)
        dup_author.all_books.add(b2)

        refresh_admin = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")

        res_merge = api_client.post(
            "/api/v1/admin/authors/merge/",
            {"canonical_id": canonical_author.id, "duplicate_ids": [dup_author.id]},
            format="json",
        )
        assert res_merge.status_code == status.HTTP_200_OK

        # Verificar que el duplicado fue eliminado y el libro reasignado
        assert not Author.objects.filter(id=dup_author.id).exists()
        b2.refresh_from_db()
        assert b2.author == canonical_author
        assert canonical_author.all_books.filter(id=b2.id).exists()

    def test_admin_user_activity_and_reports_endpoints(self, api_client, admin_user, regular_user, other_user):
        """5. Consulta de actividad y denuncias asociadas a un usuario en el panel admin."""
        # Generar actividades y post
        Activity.objects.create(
            user=regular_user,
            type=ActivityType.USER_FOLLOWED,
            metadata={"target": other_user.username},
        )
        UserPost.objects.create(
            author=regular_user,
            target_user=regular_user,
            content="Comenzando una nueva lectura fantástica.",
        )
        # Denuncia emitida por regular_user
        Report.objects.create(
            reporter=regular_user,
            content_object=other_user,
            reason=ReportReason.HARASSMENT,
            description="Mensajes insistentes.",
        )
        # Denuncia contra regular_user
        Report.objects.create(
            reporter=other_user,
            content_object=regular_user,
            reason=ReportReason.SPAM,
            description="Envío repetitivo de solicitudes.",
        )

        refresh_admin = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")

        # a) Inspección de actividad
        res_act = api_client.get(f"/api/v1/admin/users/{regular_user.id}/activity/")
        assert res_act.status_code == status.HTTP_200_OK
        data_act = res_act.json()
        assert len(data_act["activities"]) >= 1
        assert len(data_act["wall_posts"]) >= 1

        # b) Inspección de expedientes de denuncias
        res_rep = api_client.get(f"/api/v1/admin/users/{regular_user.id}/reports/")
        assert res_rep.status_code == status.HTTP_200_OK
        data_rep = res_rep.json()
        assert len(data_rep["filed_reports"]) >= 1
        assert len(data_rep["reports_against_user"]) >= 1
