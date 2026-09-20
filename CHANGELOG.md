# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning 2.0.0](https://semver.org/lang/es/).

## [Unreleased]

### Planned
- Notificaciones push mediante Web Push API.
- Internacionalización ampliada (soporte multi-idioma i18n).

---

## [1.0.0] - 2026-09-20

### Added
- **Catálogo de Libros y Autores**: Búsqueda difusa (TrigramSimilarity), filtros por género/categoría, paginación con cursor y offset, y sincronización asíncrona mediante Celery.
- **Reseñas y Calificaciones**: CRUD de reseñas, cálculo atómico de promedios de calificación, likes en reseñas y prevención de votos duplicados.
- **Sistema Social y Comunidad**:
  - Seguimiento entre usuarios (Followers/Following) con recuentos cacheados e invalidación atómica.
  - Muro de actividad / feed de lectura personalizado.
  - Clubes de lectura con foros de discusión y gestión de miembros.
  - Mensajería directa en tiempo real con WebSockets (Django Channels) y persistencia en base de datos.
- **Gamificación y Metas**:
  - Desafíos anuales de lectura y seguimiento de progreso de lectura.
  - Sistema de insignias (badges) y puntos por actividad lectora.
- **Seguridad y Moderación**:
  - Autenticación JWT con refresh tokens en rotación y blacklist.
  - Rate limiting adaptativo por endpoint y protección CSRF/CORS estricta.
  - Sistema de reportes de usuarios y moderación de contenido con soft-delete.
  - Política de cookies con consentimiento granular y banner legal (RGPD/LSSI-CE).
- **Rendimiento, Caché y Concurrencia**:
  - Estrategia de caché Redis multi-capa con invalidación granular orientada a eventos.
  - Bloqueo optimista y transacciones atómicas (`select_for_update`) contra condiciones de carrera.
  - Paginación optimizada para colecciones masivas.
- **Alta Disponibilidad y Operaciones**:
  - Endpoints de salud: liveness (`/api/v1/health/`), readiness (`/api/v1/ready/`) y versión (`/api/v1/version/`).
  - Servicios y comandos de backup automatizado para PostgreSQL y medios (`backup_db`, `backup_media`).
  - Plan de Recuperación ante Desastres (DRP) documentado con 5 runbooks y comando de reconstrucción de caché (`rebuild_cache`).
  - Métricas de observabilidad en tiempo real (`/api/v1/observability/metrics/`).
- **Frontend SPA React**:
  - Arquitectura moderna con React 18, Vite, TypeScript, TailwindCSS y Zustand.
  - TanStack Query con revalidación optimista y caché sincronizada.
  - Diseño responsivo, tema dark/light, microinteracciones y accesibilidad WCAG 2.1 AA.

### Changed
- Estandarización de versionado bajo Semantic Versioning 2.0.0 unificado en backend (`pyproject.toml`, `mybookconnect.version`) y frontend (`package.json`).
- Centralización de variables de entorno y endurecimiento de configuraciones de despliegue en Docker Compose para producción.

---

[Unreleased]: https://github.com/Zaton81/MyBookConnect/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Zaton81/MyBookConnect/releases/tag/v1.0.0
