"""
Tests exhaustivos para la Fase 3: Seguridad de autenticación y autorización (P0/P1).

Valida:
1. Revocación instantánea de Access Tokens en vuelo mediante marca temporal en Redis.
2. Generación, validación y consumo de un solo uso (single-use) de tickets efímeros WebSocket.
3. Rechazo de login en modo verificación obligatoria (REQUIRE_EMAIL_VERIFICATION) para usuarios no verificados.
4. Remitente de correos oficial noreply@mybooksocial.com en reseteo de contraseña y confirmación.
5. Protección estricta contra IDOR en listas de lectura (add_book, remove_book, reorder, retrieve).
6. Anti-enumeración 404 ante usuarios bloqueados en UserDetailView.
7. Cabeceras de seguridad HTTP (Referrer-Policy, X-Content-Type-Options, X-Frame-Options).
"""

import time

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book, ReadingList, ReadingListPrivacy
from mybookconnect.middleware import get_user_from_ticket

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestPhase03AuthSecurity:
    """Suite de pruebas para seguridad de autenticación, ciclo de vida de tokens e IDOR."""

    def test_access_token_rejected_immediately_after_session_revocation(self):
        """
        Un access token previamente emitido debe ser rechazado inmediatamente
        tras llamar a revoke-all sessions, impidiendo que siga activo durante sus 15 min de TTL.
        """
        user = User.objects.create_user(
            username="revoked_user",
            email="revoked@example.com",
            password="SecurePassword123!",
        )
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        # 1. Petición inicial válida
        res_valid = client.get("/api/v1/auth/profile/")
        assert res_valid.status_code == status.HTTP_200_OK

        # Asegurar que el timestamp de revocación sea posterior al iat del token
        time.sleep(1)

        # 2. Revocar todas las sesiones del usuario
        res_revoke = client.post("/api/v1/auth/sessions/revoke-all/")
        assert res_revoke.status_code == status.HTTP_200_OK

        # 3. Intentar acceder con el mismo access token: debe ser rechazado con 401
        res_after = client.get("/api/v1/auth/profile/")
        assert res_after.status_code == status.HTTP_401_UNAUTHORIZED
        assert "revocada" in str(res_after.data) or res_after.data.get("code") == "session_revoked"

    def test_websocket_ticket_generation_and_single_use(self):
        """
        El endpoint /api/v1/auth/ws-ticket/ genera un ticket temporal que puede ser consumido
        una única vez por el middleware de WebSocket, borrándose inmediatamente de Redis.
        """
        user = User.objects.create_user(
            username="ws_user",
            email="ws_user@example.com",
            password="SecurePassword123!",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Generar ticket
        res = client.post("/api/v1/auth/ws-ticket/")
        assert res.status_code == status.HTTP_200_OK
        ticket = res.data.get("ticket")
        assert ticket is not None
        assert res.data.get("expires_in") == 60

        # Verificar que el ticket está presente en cache
        cached_uid = cache.get(f"ws_ticket_{ticket}")
        assert cached_uid == user.id

        # 2. Consumir ticket de forma asíncrona mediante get_user_from_ticket
        import asyncio
        consumed_user = asyncio.run(get_user_from_ticket(ticket))
        assert consumed_user.id == user.id

        # 3. Consumir por segunda vez: el ticket ya no debe existir (uso único)
        second_attempt = asyncio.run(get_user_from_ticket(ticket))
        assert second_attempt.is_anonymous

    def test_invalid_and_expired_websocket_tickets(self):
        """Tickets falsos o inexistentes deben resolver a AnonymousUser."""
        import asyncio
        user = asyncio.run(get_user_from_ticket("non-existent-ticket-xyz"))
        assert user.is_anonymous

    def test_email_verification_enforcement_in_production(self):
        """
        Con REQUIRE_EMAIL_VERIFICATION=True, usuarios sin verificar son rechazados al intentar login
        con código email_not_verified y 403 Forbidden.
        """
        User.objects.create_user(
            username="unverified_user",
            email="unverified@example.com",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        User.objects.create_user(
            username="verified_user",
            email="verified@example.com",
            password="SecurePassword123!",
            is_email_verified=True,
        )

        client = APIClient()

        with override_settings(REQUIRE_EMAIL_VERIFICATION=True):
            # Intento de login de usuario no verificado
            res_bad = client.post(
                "/api/v1/auth/token/",
                {"username": "unverified_user", "password": "SecurePassword123!"},
                format="json",
            )
            assert res_bad.status_code == status.HTTP_403_FORBIDDEN
            assert res_bad.data.get("code") == "email_not_verified"

            # Intento de login de usuario verificado
            res_ok = client.post(
                "/api/v1/auth/token/",
                {"username": "verified_user", "password": "SecurePassword123!"},
                format="json",
            )
            assert res_ok.status_code == status.HTTP_200_OK
            assert "access" in res_ok.data

    def test_email_sender_is_noreply_mybooksocial(self):
        """
        Los correos automáticos de verificación y restablecimiento de contraseña deben
        enviarse con el remitente noreply@mybooksocial.com.
        """
        user = User.objects.create_user(
            username="mail_user",
            email="mail_user@example.com",
            password="SecurePassword123!",
            is_email_verified=False,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        mail.outbox.clear()

        # 1. Petición de verificación de correo
        res_verify = client.post("/api/v1/auth/email/verify-request/")
        assert res_verify.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert mail.outbox[0].from_email == "noreply@mybooksocial.com"
        assert "mail_user@example.com" in mail.outbox[0].to

        # 2. Petición de reseteo de contraseña
        mail.outbox.clear()
        res_reset = client.post(
            "/api/v1/auth/password/reset/",
            {"email": "mail_user@example.com"},
            format="json",
        )
        assert res_reset.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert mail.outbox[0].from_email == "noreply@mybooksocial.com"

    def test_idor_reading_lists_protection(self):
        """
        Un usuario atacante (User B) no puede modificar, añadir libros, reordenar
        ni eliminar listas de lectura pertenecientes a User A (IDOR).
        """
        user_a = User.objects.create_user(
            username="owner_user", email="owner@example.com", password="Password123!"
        )
        user_b = User.objects.create_user(
            username="attacker_user", email="attacker@example.com", password="Password123!"
        )
        book = Book.objects.create(title="Libro Prueba IDOR")
        list_public = ReadingList.objects.create(
            user=user_a,
            name="Lista Pública de A",
            privacy=ReadingListPrivacy.PUBLIC,
        )
        list_private = ReadingList.objects.create(
            user=user_a,
            name="Lista Privada de A",
            privacy=ReadingListPrivacy.PRIVATE,
        )

        client_b = APIClient()
        client_b.force_authenticate(user=user_b)

        # 1. User B intenta añadir libro a lista pública de A -> 403 Forbidden
        res_add = client_b.post(
            f"/api/v1/books/reading-lists/{list_public.id}/add-book/",
            {"book_id": book.id},
            format="json",
        )
        assert res_add.status_code == status.HTTP_403_FORBIDDEN

        # 2. User B intenta reordenar lista pública de A -> 403 Forbidden
        res_reorder = client_b.post(
            f"/api/v1/books/reading-lists/{list_public.id}/reorder/",
            {"items": [{"book_id": book.id, "position": 1}]},
            format="json",
        )
        assert res_reorder.status_code == status.HTTP_403_FORBIDDEN

        # 3. User B intenta modificar la lista pública de A con PATCH -> 403 Forbidden
        res_update = client_b.patch(
            f"/api/v1/books/reading-lists/{list_public.id}/",
            {"name": "Nombre Hackeado"},
            format="json",
        )
        assert res_update.status_code == status.HTTP_403_FORBIDDEN

        # 4. User B intenta eliminar la lista pública de A con DELETE -> 403 Forbidden
        res_delete = client_b.delete(f"/api/v1/books/reading-lists/{list_public.id}/")
        assert res_delete.status_code == status.HTTP_403_FORBIDDEN

        # 5. User B intenta consultar la lista privada de A por ID directo -> 404 (anti-enumeración)
        res_get_private = client_b.get(f"/api/v1/books/reading-lists/{list_private.id}/")
        assert res_get_private.status_code == status.HTTP_404_NOT_FOUND

        # 6. User B intenta añadir libro a la lista privada de A -> 404 (anti-enumeración total)
        res_add_private = client_b.post(
            f"/api/v1/books/reading-lists/{list_private.id}/add-book/",
            {"book_id": book.id},
            format="json",
        )
        assert res_add_private.status_code == status.HTTP_404_NOT_FOUND

    def test_anti_enumeration_blocked_user_profile(self):
        """
        Si User A bloquea a User B, User B recibe 404 Not Found al intentar ver el perfil de User A,
        sin filtrar que la cuenta existe o que está bloqueado (evita enumeración de perfiles).
        """
        user_a = User.objects.create_user(
            username="target_blocked", email="target@example.com", password="Password123!"
        )
        user_b = User.objects.create_user(
            username="viewer_blocked", email="viewer@example.com", password="Password123!"
        )
        # User A bloquea a User B
        user_a.blocked_users.add(user_b)

        client_b = APIClient()
        client_b.force_authenticate(user=user_b)

        res = client_b.get(f"/api/v1/users/{user_a.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert res.data.get("detail") == "Usuario no encontrado."

    def test_security_headers_present(self):
        """
        Las respuestas HTTP deben incluir las cabeceras de seguridad requeridas:
        Referrer-Policy, X-Content-Type-Options y X-Frame-Options.
        """
        client = APIClient()
        res = client.get("/api/v1/health/")
        assert res.status_code == status.HTTP_200_OK
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
