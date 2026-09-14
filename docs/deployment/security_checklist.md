# Lista de Verificación de Seguridad en Producción

Antes de publicar una versión a producción, verificar rigurosamente los siguientes puntos:

## 1. Configuración de Django
- [ ] `DEBUG = False` confirmado en configuración y variables de entorno.
- [ ] `SECRET_KEY` aleatoria, no compartida con entornos de desarrollo ni versionada en Git.
- [ ] `ALLOWED_HOSTS` restringido únicamente a los dominios autorizados de la plataforma.
- [ ] `SECURE_SSL_REDIRECT = True` y `SESSION_COOKIE_SECURE = True`.
- [ ] `CSRF_COOKIE_SECURE = True` y `CSRF_COOKIE_HTTPONLY = True`.
- [ ] Cabeceras de seguridad activas:
  - `SECURE_HSTS_SECONDS = 31536000` (HSTS estricto de 1 año).
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`.
  - `SECURE_HSTS_PRELOAD = True`.
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`.
  - `X_FRAME_OPTIONS = 'DENY'`.

## 2. Redes e Infraestructura Docker
- [ ] **Puertos 5432 y 6379 NO expuestos al host** ni a Internet pública.
- [ ] Base de datos PostgreSQL y Redis alojadas en una red interna privada.
- [ ] Límites de memoria y CPU definidos en los contenedores de Docker.
- [ ] Certificados TLS/SSL actualizados (Let's Encrypt o certificado corporativo).

## 3. Base de Datos y Copias de Seguridad
- [ ] Copias de seguridad automáticas diarias de PostgreSQL programadas y probadas.
- [ ] Rotación periódica de credenciales de usuario de base de datos.
- [ ] Usuario de base de datos con permisos mínimos necesarios sobre el esquema.
