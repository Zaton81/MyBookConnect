import logging

from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class RevocationCheckingJWTAuthentication(JWTAuthentication):
    """
    Extensión de JWTAuthentication que valida en tiempo real si el token
    fue revocado antes de su expiración natural (por ejemplo, tras cambio
    de contraseña, reseteo, cierre de sesión global o suspensión).
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user or not user.is_active:
            raise AuthenticationFailed('Usuario inactivo, suspendido o no encontrado.', code='user_inactive')

        token_iat = validated_token.get('iat')
        if token_iat is not None:
            revocation_timestamp = cache.get(f"user_jwt_revoked_at_{user.id}")
            if revocation_timestamp is not None:
                # Si el token fue emitido antes de la marca de revocación, se rechaza
                if float(token_iat) < float(revocation_timestamp):
                    logger.info("Access token rechazado por revocación de sesión para usuario %s", user.id)
                    raise AuthenticationFailed(
                        'La sesión ha sido revocada tras un cambio de credenciales o cierre de sesión global.',
                        code='session_revoked',
                    )

        return user
