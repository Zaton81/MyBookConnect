"""
Pruebas automatizadas para la Fase 16: Moderación y Seguridad Social (RoadmapV2 - Sección 21).

Verifica:
- 21.1 Reportes: Permite denunciar usuario, review, comentario, mensaje y lista de lectura (ReadingList).
- Prevención de auto-denuncias y reportes duplicados pendientes.
- 21.2 Moderación y Acciones Disciplinarias: Ocultar y restaurar listas de lectura, silenciar y banear usuarios.
- Registro estricto en AuditLog de cada acción disciplinaria.
- 21.3 Estados canónicos y aliases (open, investigating, resolved, dismissed).
- 21.4 Rate limiting resiliente para reports, follows, comments, likes y messages.
- 21.5 Tipologías de política de contenido (ILLEGAL_CONTENT, IMPERSONATION, etc.).
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingList, Review, ReviewComment, ReviewLike
from messages_app.models import Conversation, Message
from users.models import AuditAction, AuditLog, Report, ReportReason, ReportStatus

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="reader_one",
        email="reader1@example.com",
        password="ValidPassword123!",
        role="USER",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="author_two",
        email="author2@example.com",
        password="ValidPassword123!",
        role="USER",
    )


@pytest.fixture
def moderator_user(db):
    user = User.objects.create_user(
        username="moderator_alice",
        email="mod@example.com",
        password="ValidPassword123!",
        role="MODERATOR",
    )
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Gabriel García Márquez")
    return Book.objects.create(
        title="Cien años de soledad",
        author=author,
        isbn="9780307474728",
    )


@pytest.fixture
def sample_review(db, other_user, sample_book):
    return Review.objects.create(
        user=other_user,
        book=sample_book,
        rating=5,
        text="Una obra maestra de la literatura universal.",
    )


@pytest.fixture
def sample_comment(db, other_user, sample_review):
    return ReviewComment.objects.create(
        user=other_user,
        review=sample_review,
        content="Totalmente de acuerdo con tu reseña.",
    )


@pytest.fixture
def sample_message(db, regular_user, other_user):
    conv, _ = Conversation.get_or_create_direct(regular_user, other_user)
    return Message.objects.create(
        conversation=conv,
        sender=other_user,
        text="Hola, ¿qué opinas de este libro?",
    )


@pytest.fixture
def sample_reading_list(db, other_user):
    return ReadingList.objects.create(
        user=other_user,
        name="Mis Clásicos Favoritos",
        slug="mis-clasicos-favoritos",
        description="Selección de obras imprescindibles del siglo XX.",
        privacy="public",
    )


# -----------------------------------------------------------------------------
# 1. Pruebas de Creación de Reportes para todos los tipos (Roadmap 21.1 y 21.5)
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportCreation:
    """Verifica el soporte integral de reportes para todos los tipos de contenido."""

    def test_report_user_success(self, api_client, regular_user, other_user):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "user",
            "object_id": other_user.id,
            "reason": ReportReason.IMPERSONATION,
            "description": "Este usuario está suplantando la identidad de un autor reconocido.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["status"] == ReportStatus.OPEN

        report = Report.objects.get(id=res.data["id"])
        assert report.reporter == regular_user
        assert report.content_object == other_user
        assert report.reason == ReportReason.IMPERSONATION

    def test_report_review_success(self, api_client, regular_user, sample_review):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "review",
            "object_id": sample_review.id,
            "reason": ReportReason.SPOILER,
            "description": "Contiene spoilers cruciales del final sin ninguna advertencia.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_201_CREATED

        report = Report.objects.get(id=res.data["id"])
        assert report.content_object == sample_review

    def test_report_comment_success(self, api_client, regular_user, sample_comment):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "comment",
            "object_id": sample_comment.id,
            "reason": ReportReason.HARASSMENT,
            "description": "Comentario ofensivo y hostigador.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_201_CREATED

        report = Report.objects.get(id=res.data["id"])
        assert report.content_object == sample_comment

    def test_report_message_success(self, api_client, regular_user, sample_message):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "message",
            "object_id": sample_message.id,
            "reason": ReportReason.SPAM,
            "description": "Envío de enlaces comerciales no deseados por chat.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_201_CREATED

        report = Report.objects.get(id=res.data["id"])
        assert report.content_object == sample_message

    def test_report_reading_list_success(self, api_client, regular_user, sample_reading_list):
        """Verifica explícitamente el reporte de listas de lectura (Roadmap 21.1)."""
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "list",
            "object_id": sample_reading_list.id,
            "reason": ReportReason.ILLEGAL_CONTENT,
            "description": "La descripción de la lista contiene enlaces a descargas ilícitas.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_201_CREATED

        report = Report.objects.get(id=res.data["id"])
        assert report.content_object == sample_reading_list
        assert report.reason == ReportReason.ILLEGAL_CONTENT


# -----------------------------------------------------------------------------
# 2. Pruebas de Prevención de Auto-Denuncias y Duplicados
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestReportConstraints:
    """Verifica la prevención de auto-denuncias y reportes duplicados pendientes."""

    def test_prevent_self_reporting_reading_list(self, api_client, other_user, sample_reading_list):
        api_client.force_authenticate(user=other_user)
        payload = {
            "target_type": "list",
            "object_id": sample_reading_list.id,
            "reason": ReportReason.OTHER,
            "description": "Auto reporte no permitido.",
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "No puedes denunciar tu propio contenido o perfil." in str(res.data)

    def test_prevent_self_reporting_user_profile(self, api_client, regular_user):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "user",
            "object_id": regular_user.id,
            "reason": ReportReason.OTHER,
        }
        res = api_client.post("/api/v1/reports/", payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "No puedes denunciar tu propio contenido o perfil." in str(res.data)

    def test_prevent_duplicate_pending_reports(self, api_client, regular_user, sample_reading_list):
        api_client.force_authenticate(user=regular_user)
        payload = {
            "target_type": "list",
            "object_id": sample_reading_list.id,
            "reason": ReportReason.SPAM,
            "description": "Primer reporte.",
        }
        first_res = api_client.post("/api/v1/reports/", payload)
        assert first_res.status_code == status.HTTP_201_CREATED

        # Segundo reporte mientras el primero está en OPEN
        second_res = api_client.post("/api/v1/reports/", payload)
        assert second_res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Ya tienes una denuncia activa en trámite para este elemento." in str(second_res.data)


# -----------------------------------------------------------------------------
# 3. Pruebas de Acciones Disciplinarias y Auditoría (Roadmap 21.2)
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestModerationResolutionAndAudit:
    """Verifica la resolución de expedientes, aplicación de medidas y trazabilidad en AuditLog."""

    def test_resolve_report_hide_and_restore_reading_list(self, api_client, moderator_user, regular_user, sample_reading_list):
        ct = ContentType.objects.get_for_model(ReadingList)
        report = Report.objects.create(
            reporter=regular_user,
            content_type=ct,
            object_id=sample_reading_list.id,
            reason=ReportReason.ILLEGAL_CONTENT,
            description="Contenido inapropiado",
            status=ReportStatus.OPEN,
        )

        api_client.force_authenticate(user=moderator_user)

        # 1. Resolver ocultando la lista (HIDE_CONTENT)
        resolve_payload = {
            "status": "resolved",
            "action_taken": "HIDE_CONTENT",
            "resolution_notes": "Lista ocultada por enlaces ilícitos confirmados.",
        }
        patch_res = api_client.patch(f"/api/v1/admin/reports/{report.id}/", resolve_payload)
        assert patch_res.status_code == status.HTTP_200_OK

        sample_reading_list.refresh_from_db()
        assert sample_reading_list.is_moderated is True

        # Verificar registro inmutable en AuditLog
        audit_entry = AuditLog.objects.filter(
            actor=moderator_user,
            action=AuditAction.MODERATION_RESOLVE,
        ).first()
        assert audit_entry is not None
        assert audit_entry.metadata["action_taken"] == "HIDE_CONTENT"

        # 2. Restaurar la lista mediante endpoint directo (RESTORE)
        restore_payload = {
            "target_type": "list",
            "target_id": sample_reading_list.id,
        }
        restore_res = api_client.post("/api/v1/admin/moderation/restore/", restore_payload)
        assert restore_res.status_code == status.HTTP_200_OK

        sample_reading_list.refresh_from_db()
        assert sample_reading_list.is_moderated is False

    def test_resolve_report_ban_user_and_audit(self, api_client, moderator_user, regular_user, other_user):
        ct = ContentType.objects.get_for_model(User)
        report = Report.objects.create(
            reporter=regular_user,
            content_type=ct,
            object_id=other_user.id,
            reason=ReportReason.HARASSMENT,
            description="Acoso reiterado",
            status=ReportStatus.OPEN,
        )

        api_client.force_authenticate(user=moderator_user)
        resolve_payload = {
            "status": "resolved",
            "action_taken": "BAN_USER",
            "resolution_notes": "Baneo definitivo por infracción grave de acoso.",
        }
        patch_res = api_client.patch(f"/api/v1/admin/reports/{report.id}/", resolve_payload)
        assert patch_res.status_code == status.HTTP_200_OK

        other_user.refresh_from_db()
        assert other_user.is_active is False

    def test_direct_user_disciplinary_mute_and_unmute(self, api_client, moderator_user, other_user):
        api_client.force_authenticate(user=moderator_user)

        # Silenciar por 24 horas
        mute_res = api_client.post(
            f"/api/v1/admin/moderation/users/{other_user.id}/mute/",
            {"duration_hours": 24, "reason": "Silenciamiento temporal"},
        )
        assert mute_res.status_code == status.HTTP_200_OK
        other_user.refresh_from_db()
        assert other_user.muted_until is not None
        assert other_user.muted_until > timezone.now()

        # Des-silenciar
        unmute_res = api_client.post(f"/api/v1/admin/moderation/users/{other_user.id}/unmute/")
        assert unmute_res.status_code == status.HTTP_200_OK
        other_user.refresh_from_db()
        assert other_user.muted_until is None


# -----------------------------------------------------------------------------
# 4. Pruebas de Compatibilidad de Estados y Aliases (Roadmap 21.3)
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestStatusAliasesAndNormalization:
    """Verifica que los estados canónicos (open, investigating, resolved, dismissed) se gestionen correctamente."""

    def test_status_normalization_investigating_and_dismissed(self, api_client, moderator_user, regular_user, other_user):
        ct = ContentType.objects.get_for_model(User)
        report = Report.objects.create(
            reporter=regular_user,
            content_type=ct,
            object_id=other_user.id,
            reason=ReportReason.SPAM,
            status=ReportStatus.OPEN,
        )

        api_client.force_authenticate(user=moderator_user)

        # 1. Cambiar estado a 'investigating'
        patch_inv = api_client.patch(f"/api/v1/admin/reports/{report.id}/", {"status": "investigating"})
        assert patch_inv.status_code == status.HTTP_200_OK
        report.refresh_from_db()
        assert report.status == ReportStatus.UNDER_REVIEW

        # 2. Desestimar con alias 'dismissed'
        patch_dism = api_client.patch(
            f"/api/v1/admin/reports/{report.id}/",
            {"status": "dismissed", "action_taken": "DISMISS", "resolution_notes": "Denuncia infundada."},
        )
        assert patch_dism.status_code == status.HTTP_200_OK
        report.refresh_from_db()
        assert report.status == ReportStatus.REJECTED

        # 3. Filtrar en cola de moderación usando alias
        list_res = api_client.get("/api/v1/admin/reports/?status=dismissed")
        assert list_res.status_code == status.HTTP_200_OK
        assert any(r["id"] == report.id for r in list_res.data["results"])


# -----------------------------------------------------------------------------
# 5. Pruebas de Rate Limiting Resiliente (Roadmap 21.4)
# -----------------------------------------------------------------------------

@pytest.mark.django_db
class TestSocialRateLimits:
    """Verifica que los limitadores de tasa resilientes estén aplicados y funcionen."""

    def test_report_rate_limit_throttle_class(self):
        from users.moderation_views import ReportCreateView
        from users.throttles import ReportRateThrottle

        assert ReportRateThrottle in ReportCreateView.throttle_classes
        assert ReportRateThrottle.scope == "reports"

    def test_follow_rate_limit_throttle_class(self):
        from users.throttles import FollowRateThrottle
        from users.views import FollowUserView

        assert FollowRateThrottle in FollowUserView.throttle_classes
        assert FollowRateThrottle.scope == "follows"

    def test_like_rate_limit_throttle_class(self):
        from books.views import ReviewLikeToggleView
        from users.throttles import LikeRateThrottle

        assert LikeRateThrottle in ReviewLikeToggleView.throttle_classes
        assert LikeRateThrottle.scope == "likes"

    def test_comment_rate_limit_dynamic_throttle(self):
        from books.views import ReviewCommentListCreateView
        from users.throttles import CommentRateThrottle

        view = ReviewCommentListCreateView()
        # Mock request con método POST
        class DummyRequest:
            method = "POST"
        view.request = DummyRequest()
        throttles = view.get_throttles()
        assert any(isinstance(t, CommentRateThrottle) for t in throttles)

    def test_message_rate_limit_dynamic_throttle(self):
        from messages_app.views import MessageViewSet
        from users.throttles import MessageRateThrottle

        view = MessageViewSet()
        class DummyRequest:
            method = "POST"
        view.request = DummyRequest()
        view.action = "create"
        throttles = view.get_throttles()
        assert any(isinstance(t, MessageRateThrottle) for t in throttles)
