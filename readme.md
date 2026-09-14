# MyBookConnect 📚

[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-Passing-brightgreen)](https://github.com/Zaton81/MyBookConnect)
[![Django](https://img.shields.io/badge/Django-5.2%20LTS-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.18.1-red)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7%2B-DC382D?logo=redis)](https://redis.io/)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9%20Strict-3178C6?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.4.3-646CFF?logo=vite)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)

**MyBookConnect** es una plataforma web full-stack y red social literaria diseñada para lectores y comunidades de entusiastas de los libros. Integra biblioteca personal de lectura, seguimiento social, mensajería en tiempo real mediante WebSockets, un motor híbrido de recomendaciones, búsqueda de catálogo enriquecida con trigramas y capacidades de inteligencia artificial contextual compatible con APIs OpenAI.

---

## 🌟 Características Principales

- 📖 **Biblioteca Personal Avanzada**: Gestión de estados de lectura (`want_to_read`, `reading`, `read`, `abandoned`), barra de progreso por páginas, formatos físicos/digitales y lista de deseos.
- ✍️ **Reseñas y Calificaciones Públicas**: Separación estricta entre la estantería privada del usuario (`UserBook`) y la opinión comunitaria (`Review`).
- 👥 **Red Social Literaria**: Feed de actividad social de lectores seguidos, sistema de bloqueos, perfiles con niveles de privacidad granular y gestión de seguidores.
- 💬 **Mensajería en Tiempo Real**: Salas de chat uno a uno impulsadas por Django Channels sobre WebSockets con autenticación JWT segura y respaldo en Redis Channel Layer.
- 🧠 **Motor Híbrido de Recomendaciones**: Algoritmo de sugerencias basado en afinidad de géneros, libros leídos con alta calificación, popularidad ponderada y retroalimentación explícita del usuario.
- ⚡ **Búsqueda Avanzada y Enriquecimiento**: Búsqueda difusa y por similitud de trigramas en PostgreSQL (`pg_trgm`) y tareas asíncronas en Celery para autocompletado desde Google Books, OpenLibrary y Wikipedia.
- 🤖 **Asistente Literario con IA**: Generación de resúmenes contextuales, búsqueda semántica y ejecución controlada de herramientas externas con validación de seguridad contra prompt injection.
- 🛡️ **Seguridad y Observabilidad**: Autenticación SimpleJWT con rotación de refresh tokens y blacklist en BD, limitación de tasa (Rate Limiting), logging estructurado en JSON con redacción de credenciales y cuadro de mando de métricas operativas.

---

## 🏗️ Arquitectura del Sistema

```text
                     Internet / Navegador Cliente
                                  │
                          [ React 18 + Vite ]
                          [ TypeScript Strict ]
                                  │
                                  ▼
                   [ Nginx / Reverse Proxy (Prod) ]
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        ▼                                                   ▼
[ Gunicorn / WSGI (HTTP) ]                        [ Daphne / ASGI (WS) ]
[ Django 5.2 + DRF ]                              [ Django Channels 4 ]
        │                                                   │
        └─────────────────────────┬─────────────────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               ▼                  ▼                  ▼
     [ PostgreSQL 16 ]     [ Redis 7 ]        [ Celery Worker ]
     - Fuente de verdad    - Caché central    - Tareas en segundo plano
     - Índices Trigram/GIN - Channel Layer    - Descarga de portadas
     - Integridad relacional- Rate limiting   - Enriquecimiento externo
```

---

## 🚀 Inicio Rápido con Docker

### Requisitos Previos
- [Docker Engine](https://docs.docker.com/engine/install/) versión 24+
- [Docker Compose v2](https://docs.docker.com/compose/)
- [Node.js](https://nodejs.org/) 20+ y `pnpm` (opcional, para desarrollo frontend local)

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Zaton81/MyBookConnect.git
cd MyBookConnect
```

### 2. Configuración de Variables de Entorno
```bash
# Variables del backend
cp backend/.env.example backend/.env

# Variables del entorno raíz
cp .env.example .env
```
Edite `backend/.env` para configurar claves de seguridad y credenciales seguras.

### 3. Construir y Levantar los Contenedores
```bash
# Entorno de Desarrollo
docker compose up -d --build

# Verificar el estado de los contenedores
docker compose ps
```

Una vez desplegado:
- **Frontend SPA**: [http://localhost:5173](http://localhost:5173)
- **Backend API REST**: [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
- **Documentación Swagger / OpenAPI**: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
- **Métricas de Observabilidad (Admin)**: [http://localhost:8000/api/v1/observability/metrics/](http://localhost:8000/api/v1/observability/metrics/)

---

## 🧪 Pruebas y Validación Continua

La plataforma cuenta con cobertura de pruebas automatizadas en frontend y backend:

### Tests de Backend (Pytest + PostgreSQL + Redis)
```bash
# Ejecutar suite completa (307 tests)
docker compose exec -T backend pytest -q

# Ejecutar tests de rendimiento y SLAs
docker compose exec -T backend pytest -q tests/test_phase43_performance.py

# Ejecutar perfilado de consultas EXPLAIN ANALYZE
docker compose exec -T backend python manage.py benchmark_queries
```

### Tests de Frontend (Vitest + Testing Library)
```bash
cd frontend

# Verificación de tipos estricta (TypeScript)
npm run typecheck

# Pruebas unitarias y de componentes (21 tests)
npx vitest run

# Construcción del bundle de producción
npm run build
```

---

## 📚 Documentación Técnica

La documentación exhaustiva y especializada se organiza en el directorio [`docs/`](./docs/):

- 🏛️ **[Arquitectura](./docs/architecture/overview.md)**: Visión global, diseño en capas y subsistemas.
- 🗄️ **[Modelo de Datos](./docs/architecture/data_model.md)**: Esquema de base de datos relacional y restricciones de integridad.
- ⚡ **[Caché y WebSockets](./docs/architecture/caching_and_channels.md)**: Redis caching, TTLs y capas de comunicación en tiempo real.
- 🔍 **[IA y Búsqueda](./docs/architecture/ai_and_search.md)**: Trigramas, vectorización y seguridad contra inyección de prompts.
- 🔌 **[Referencia de API](./docs/api/overview.md)**: Catálogo de endpoints OpenAPI, contratos de autenticación y códigos de error.
- 💻 **[Guía de Desarrollo](./docs/development/getting_started.md)**: Entorno local, estándares de código y linters.
- 🚢 **[Despliegue y Producción](./docs/deployment/docker_production.md)**: Guía para entornos de producción y checklist de seguridad.
- 🛡️ **[Seguridad](./docs/security/threat_model_and_hardening.md)**: Modelo de amenazas, endurecimiento JWT y auditoría.
- 📜 **[Decisiones de Arquitectura (ADRs)](./docs/decisions/)**:
  - [ADR-001: Desacoplamiento Django + React](./docs/decisions/ADR-001-django-react.md)
  - [ADR-002: PostgreSQL como Fuente Única de Verdad](./docs/decisions/ADR-002-postgresql-source-of-truth.md)
  - [ADR-003: Estrategia de Caché y Canales con Redis](./docs/decisions/ADR-003-redis-caching-and-channels.md)
  - [ADR-004: Tareas Asíncronas con Celery](./docs/decisions/ADR-004-celery-async-workers.md)
  - [ADR-005: Estrategia de Seguridad y Autenticación JWT](./docs/decisions/ADR-005-jwt-security-strategy.md)
  - [ADR-006: Separación de Responsabilidades Review vs UserBook](./docs/decisions/ADR-006-review-userbook-separation.md)
  - [ADR-007: Búsqueda Híbrida con Trigramas y Semántica](./docs/decisions/ADR-007-search-and-trigrams.md)
  - [ADR-008: Motor de Recomendaciones Literarias Híbrido](./docs/decisions/ADR-008-recommendation-engine.md)

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia MIT. Consulta el archivo `LICENSE` para más información.
