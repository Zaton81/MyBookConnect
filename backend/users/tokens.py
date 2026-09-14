from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Generador de tokens efímeros y criptográficamente seguros para validación de correo electrónico.
    El hash depende del estado de verificación, email y clave primaria, asegurando
    que el token quede invalidado de inmediato tras su uso.
    """
    def _make_hash_value(self, user, timestamp):
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, '') or ''
        return f"{user.pk}{user.is_email_verified}{email}{timestamp}"


email_verification_token_generator = EmailVerificationTokenGenerator()


def encode_uid(user_id) -> str:
    """Codifica el identificador numérico de usuario en base64 urlsafe."""
    return urlsafe_base64_encode(force_bytes(user_id))


def decode_uid(uidb64: str) -> int | None:
    """Decodifica un UID en base64 urlsafe a identificador numérico de usuario."""
    try:
        raw_id = force_str(urlsafe_base64_decode(uidb64))
        return int(raw_id)
    except (TypeError, ValueError, OverflowError):
        return None
