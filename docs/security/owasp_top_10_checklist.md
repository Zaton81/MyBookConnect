# Auditoría y Checklist OWASP Top 10 — MyBookConnect

Este documento certifica el análisis y los controles técnicos implementados en **MyBookConnect** frente al estándar **OWASP Top 10:2021** para garantizar un despliegue seguro en producción pública (Fase A4 del Roadmap v2.0).

---

## Matriz de Cumplimiento OWASP Top 10

| Identificador OWASP | Categoría de Vulnerabilidad | Estado | Controles Técnicos Implementados en MyBookConnect |
| :--- | :--- | :--- | :--- |
| **A01:2021** | **Broken Access Control** (Control de Acceso Defectuoso) | **SUPERADO** | - Permisos declarativos por endpoint (`IsAuthenticated`, `IsAdminUser`, `IsOwnerOrReadOnly`).<br>- Políticas de visibilidad en `users/policies.py` y `PrivacyService`.<br>- Bloqueos sociales bidireccionales devuelven `404 Not Found` (anti-enumeración).<br>- Filtrado de recursos por `request.user` para prevenir IDOR en listas, reseñas y métricas.<br>- Tokens no accesibles desde JavaScript (cookies `HttpOnly; SameSite=Lax; Secure`). |
| **A02:2021** | **Cryptographic Failures** (Fallos Criptográficos) | **SUPERADO** | - Forzado estricto de HTTPS mediante `SECURE_SSL_REDIRECT` y HSTS (`Strict-Transport-Security: max-age=31536000`).<br>- Backups de base de datos cifrados mediante `AES-256-CBC` con manifiesto criptográfico SHA-256.<br>- Contraseñas de usuario hasheadas con PBKDF2/SHA-256.<br>- Algoritmos de hash seguros (migración de MD5 a SHA-256 en cache keys y deduplicación). |
| **A03:2021** | **Injection** (Inyecciones: SQL, XSS, Prompt Injection, SSRF) | **SUPERADO** | - Consultas SQL parametrizadas al 100% mediante Django ORM; cero SQL crudo sin escapar.<br>- Sanitización de entradas HTML con `bleach` en reseñas, comentarios y biografías (`html_sanitizer.py`).<br>- Guardrails de IA contra prompt injection y validación de contexto literario en `ai/guardrails.py`.<br>- Validación estricta anti-SSRF en `cover_service.py` (`validate_safe_external_url`). |
| **A04:2021** | **Insecure Design** (Diseño Inseguro) | **SUPERADO** | - Throttling agresivo y resiliente (`book_import`, `enrichment`, `author_claims`, `reports`, `auth`).<br>- Decorador `@idempotent` para evitar duplicidad de transacciones críticas.<br>- Backpressure y control de tamaño en WebSockets (`ChatConsumer` máx 64KB, 10 msg/s). |
| **A05:2021** | **Security Misconfiguration** (Configuración Errónea de Seguridad) | **SUPERADO** | - Cabeceras de seguridad activas: CSP (`Content-Security-Policy`), COOP (`Cross-Origin-Opener-Policy`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`.<br>- `DEBUG = False` obligatorio en producción.<br>- Sondas `/health/live` y `/health/ready` desacopladas; ante caída de DB/Redis retornan `503` sanitizado sin filtrar trazas ni credenciales.<br>- Ruta de administración ofuscada con honeypot trap (`admin_probe_trap_view`). |
| **A06:2021** | **Vulnerable and Outdated Components** (Componentes Vulnerables u Obsoletos) | **SUPERADO** | - Escaneo automatizado SAST con Bandit y auditoría de paquetes con `pip-audit` en GitHub Actions.<br>- Contenedores Docker multi-stage ejecutados bajo usuarios no-root.<br>- Dependabot configurado para dependencias de backend y frontend. |
| **A07:2021** | **Identification and Authentication Failures** (Fallos de Identificación y Autenticación) | **SUPERADO** | - JWT con rotación obligatoria de `refresh_token` y lista negra persistente (`BlacklistedToken`).<br>- Vida corta de tokens de acceso (15 minutos).<br>- Erradicación de autenticación por query string (`?token=`) en WebSockets; uso exclusivo de tickets efímeros `/api/v1/auth/ws-ticket/` de un solo uso o cookies HttpOnly.<br>- Rate limiting específico en `/api/v1/auth/token/` y `/password/reset/`. |
| **A08:2021** | **Software and Data Integrity Failures** (Fallos de Integridad de Software y Datos) | **SUPERADO** | - Bloqueo de concurrencia y transacciones atómicas (`transaction.atomic()` y `select_for_update()`) en operaciones críticas (rating, importaciones, transferencias).<br>- Constraints de modelo únicos y checks (`UniqueConstraint`, `CheckConstraint`).<br>- Validación de firmas y checksums de backups en scripts de recuperación. |
| **A09:2021** | **Security Logging and Monitoring Failures** (Fallos en Logs y Monitorización) | **SUPERADO** | - Logging estructurado en formato JSON estándar (`StructuredLoggingMiddleware`).<br>- Trazabilidad distribuida con inyección de cabecera `request_id` (UUIDv4) en cada petición.<br>- Sanitización automática de campos sensibles (`password`, `token`, `secret`, `authorization`, `credit_card`) antes de escribir a stdout o archivo.<br>- Endpoints de observabilidad `/api/v1/observability/metrics/` protegidos con `IsAdminUser`. |
| **A10:2021** | **Server-Side Request Forgery** (SSRF) | **SUPERADO** | - Validador `validate_safe_external_url` en descarga de portadas e imágenes de catálogo.<br>- Resolución previa por DNS (`socket.getaddrinfo`) y comprobación de que ninguna IP pertenezca a redes privadas (RFC 1918: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), metadata cloud (`169.254.169.254`), link-local o no enrutables.<br>- Comprobación anti-SSRF recurrente en cada salto de redirección HTTP. |

---

## Verificación Continua en CI/CD

El pipeline de integración continua (`.github/workflows/security.yml`, `ci-backend.yml`, `ci-frontend.yml`) verifica en cada Pull Request:
1. `bandit -r backend/` (SAST de seguridad Python).
2. `pip-audit` (Análisis de vulnerabilidades conocidas en librerías).
3. `pnpm audit` (Análisis de dependencias frontend).
4. `pytest tests/test_phase_a*.py` (Pruebas unitarias y de integración de seguridad).
