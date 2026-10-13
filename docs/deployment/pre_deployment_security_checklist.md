# Checklist de Seguridad y Pre-Despliegue — My Book Social

**Documento de Gobernanza y Operaciones (Roadmap v2.0 — Fase E1)**  
**Versión:** 1.0.0 (SemVer 2.0.0)  
**Dominio:** `mybooksocial.com` / `staging.mybooksocial.com`

Este checklist debe ser auditado y firmado obligatoriamente antes de promover cualquier versión desde la rama `develop` a `main` o desplegar a entornos de Staging y Producción.

---

## 1. Parámetros Críticos de Seguridad de la Aplicación (Django)

- [ ] **DEBUG:** `DEBUG = False` confirmado en variables de entorno de producción.
- [ ] **SECRET_KEY:** Clave criptográfica aleatoria de 50+ caracteres de alta entropía, inyectada vía secretos o `.env`, nunca commiteada en el repositorio.
- [ ] **ALLOWED_HOSTS:** Restringido explícitamente a `['mybooksocial.com', 'www.mybooksocial.com', 'api.mybooksocial.com', 'staging.mybooksocial.com']`.
- [ ] **Cabeceras de Seguridad HTTP (HSTS / Sniff / Framing):**
  - `SECURE_HSTS_SECONDS = 31536000` (1 año estricto).
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`.
  - `SECURE_HSTS_PRELOAD = True`.
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`.
  - `X_FRAME_OPTIONS = 'DENY'`.
- [ ] **Cookies Seguras (JWT / Sesión / CSRF):**
  - Access Token y Refresh Token emitidos en cookies `HttpOnly = True`, `Secure = True`, `SameSite = 'Lax'`.
  - `CSRF_COOKIE_SECURE = True`, `CSRF_COOKIE_HTTPONLY = True`.
  - Tokens JWT completamente erradicados de `localStorage` en clientes frontend.
- [ ] **WebSockets Seguros:**
  - Autenticación por query string (`?token=...`) bloqueada en Daphne.
  - Handshake condicionado a tickets efímeros criptográficos (`/api/v1/auth/ws-ticket/`).

---

## 2. Redes, Aislamiento y Topología Docker

- [ ] **Aislamiento de Redes (`docker-compose.prod.yml`):**
  - Red `backend_net` configurada con `internal: true`.
  - **Puertos de PostgreSQL (5432) y Redis (6379) NO expuestos al host ni a la interfaz pública**.
  - Nginx como único punto de entrada público (puertos 80 y 443).
- [ ] **Recursos y Cuotas:**
  - Límites de CPU y memoria configurados en todos los contenedores (`deploy.resources.limits`).
- [ ] **Apagado Limpio y Señales:**
  - `stop_signal: SIGTERM` y `stop_grace_period: 30s` en Daphne y Celery.
- [ ] **Certificados SSL/TLS:**
  - Soporte TLS 1.2 y 1.3 configurado en `frontend/nginx.ssl.conf.template`.
  - Renovación automática mediante contenedor Certbot.

---

## 3. Base de Datos, Migraciones y Restauración (DRP)

- [ ] **Migraciones:** Cero migraciones pendientes (`python manage.py makemigrations --check --dry-run`).
- [ ] **Backup y Frescura:** Copia de seguridad diaria cifrada (AES-256) programada y auditada con `check_backup_freshness`.
- [ ] **Prueba de Restore Completa:** Verificación de restauración ejecutada con éxito mediante `python manage.py verify_restore_integrity` sobre catálogo, usuarios, reseñas y portadas.

---

## 4. Control de Acceso y Feature Flags de Lanzamiento

- [ ] **Registro Público y Cohortes Beta:**
  - `PUBLIC_REGISTRATION_ENABLED`: Evaluada según la fase de lanzamiento (False en beta cerrada, True en beta abierta).
  - `REQUIRE_BETA_INVITATION`: Evaluada para control de invitaciones en caso de soft launch.
- [ ] **Superficie de Ataque y Observabilidad:**
  - Endpoints de métricas (`/metrics/`) protegidos exclusivamente para administradores (`IsAdminUser`).
  - Sondas `/health/live` y `/health/ready` operativas con respuestas JSON sanitizadas sin filtrar trazas ni credenciales.
