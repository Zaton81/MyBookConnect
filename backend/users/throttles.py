from mybookconnect.throttling import ResilientAnonRateThrottle, ResilientSimpleRateThrottle


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
