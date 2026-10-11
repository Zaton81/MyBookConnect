from datetime import timedelta
from django.conf import settings
from rest_framework.response import Response


def set_auth_cookies(
    response: Response,
    access_token: str | None = None,
    refresh_token: str | None = None,
) -> Response:
    """
    Establece cookies HttpOnly seguras para access_token y refresh_token.
    Protege las credenciales de sesión contra ataques XSS al impedir acceso desde JavaScript.
    """
    cookie_access_name = getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token')
    cookie_refresh_name = getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token')
    secure = getattr(settings, 'AUTH_COOKIE_SECURE', not settings.DEBUG)
    httponly = getattr(settings, 'AUTH_COOKIE_HTTPONLY', True)
    samesite = getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')
    path = getattr(settings, 'AUTH_COOKIE_PATH', '/')
    domain = getattr(settings, 'AUTH_COOKIE_DOMAIN', None)

    simple_jwt = getattr(settings, 'SIMPLE_JWT', {})
    access_lifetime = simple_jwt.get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=15))
    refresh_lifetime = simple_jwt.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))

    if access_token:
        max_age = int(access_lifetime.total_seconds())
        response.set_cookie(
            key=cookie_access_name,
            value=access_token,
            max_age=max_age,
            httponly=httponly,
            secure=secure,
            samesite=samesite,
            path=path,
            domain=domain,
        )

    if refresh_token:
        max_age = int(refresh_lifetime.total_seconds())
        response.set_cookie(
            key=cookie_refresh_name,
            value=refresh_token,
            max_age=max_age,
            httponly=httponly,
            secure=secure,
            samesite=samesite,
            path=path,
            domain=domain,
        )

    return response


def delete_auth_cookies(response: Response) -> Response:
    """
    Elimina las cookies de autenticación HttpOnly al cerrar sesión o revocar credenciales.
    """
    cookie_access_name = getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token')
    cookie_refresh_name = getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token')
    path = getattr(settings, 'AUTH_COOKIE_PATH', '/')
    domain = getattr(settings, 'AUTH_COOKIE_DOMAIN', None)
    samesite = getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax')

    response.delete_cookie(
        key=cookie_access_name,
        path=path,
        domain=domain,
        samesite=samesite,
    )
    response.delete_cookie(
        key=cookie_refresh_name,
        path=path,
        domain=domain,
        samesite=samesite,
    )
    return response
