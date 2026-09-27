from mybookconnect.throttling import (
    ResilientAnonRateThrottle,
    ResilientSimpleRateThrottle,
    ResilientUserRateThrottle,
)


class AuthAnonRateThrottle(ResilientAnonRateThrottle):
    """
    Limitador estricto para operaciones de autenticación anónimas (registro, solicitud de tokens).
    Previene abusos de scraping o creación masiva de cuentas.
    """
    scope = 'auth_anon'


class LoginRateThrottle(ResilientSimpleRateThrottle):
    """
    Limitador de velocidad para intentos de inicio de sesión (/api/v1/auth/token/).
    Mitiga ataques de fuerza bruta, adivinación de contraseñas y credential stuffing.
    Usa la dirección IP del cliente y opcionalmente el username suministrado.
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        username = request.data.get('username') or ''
        if username:
            cleaned_user = str(username).strip().lower()
            return self.cache_format % {
                'scope': self.scope,
                'ident': f"{ident}_{cleaned_user}",
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }


class PasswordResetRateThrottle(ResilientSimpleRateThrottle):
    """
    Limitador de velocidad para solicitudes de restablecimiento de contraseña.
    Evita bombardeo de correos y saturación de la pasarela SMTP.
    """
    scope = 'password_reset'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        email = request.data.get('email') or ''
        if email:
            cleaned_email = str(email).strip().lower()
            return self.cache_format % {
                'scope': self.scope,
                'ident': f"{ident}_{cleaned_email}",
            }
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }


# --- Throttles de Seguridad y Moderación Social (Roadmap 21.4) ---

class ReportRateThrottle(ResilientUserRateThrottle):
    """Evita el spam y abuso de denuncias a moderación (Roadmap 21.4)."""
    scope = 'reports'


class FollowRateThrottle(ResilientUserRateThrottle):
    """Evita operaciones de follow/unfollow masivas automatizadas (Roadmap 21.4)."""
    scope = 'follows'


class CommentRateThrottle(ResilientUserRateThrottle):
    """Evita el spam y flood de comentarios en reseñas literarias (Roadmap 21.4)."""
    scope = 'comments'


class LikeRateThrottle(ResilientUserRateThrottle):
    """Evita la automatización y spam de likes/unlikes en reseñas (Roadmap 21.4)."""
    scope = 'likes'


class MessageRateThrottle(ResilientUserRateThrottle):
    """Evita el flood y spam masivo de mensajería directa (Roadmap 21.4)."""
    scope = 'messages'
