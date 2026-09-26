# Pipeline de CI/CD y Calidad Continua (Fase 12)

Este documento detalla la arquitectura, configuración y estándares de ejecución del pipeline de Integración y Entrega Continua (CI/CD) de BookSocial / MyBookConnect, implementado mediante **GitHub Actions** y contenedores Docker.

---

## 1. Arquitectura y Flujo de Trabajo

El objetivo primordial del pipeline es impedir que cualquier regresión, fallo de estilo, error de tipos, vulnerabilidad conocida o migración de base de datos pendiente llegue a la rama `develop` o a `main` (producción).

```text
git push / pull_request (develop, main)
   ├── .github/workflows/ci-backend.yml
   │     ├── Linting con Ruff
   │     ├── Chequeo de migraciones ORM sin aplicar (makemigrations --check)
   │     └── Pruebas automatizadas (Pytest) con PostgreSQL 16 y Redis 7 reales
   │
   ├── .github/workflows/ci-frontend.yml
   │     ├── Verificación de estilo Prettier (format:check)
   │     ├── Linter ESLint (React, Hooks, TS, A11y)
   │     ├── Comprobación estricta de tipos (TypeScript tsc --noEmit)
   │     ├── Suite de pruebas unitarias y de componentes (Vitest)
   │     └── Compilación del bundle de producción (Vite build)
   │
   ├── .github/workflows/ci-docker.yml
   │     ├── Compilación de imagen Docker de backend (Python 3.12-slim)
   │     └── Compilación de imagen Docker de frontend multi-stage (Node 22 -> Nginx)
   │
   ├── .github/workflows/security.yml
   │     ├── Análisis estático de seguridad Python (Bandit SAST)
   │     ├── Auditoría de vulnerabilidades en pip (pip-audit)
   │     └── Auditoría de vulnerabilidades en npm/pnpm (pnpm audit)
   │
   └── .github/dependabot.yml
         ├── Actualizaciones semanales de dependencias Python (pip)
         ├── Actualizaciones semanales de dependencias Node (npm/pnpm)
         └── Actualizaciones mensuales de GitHub Actions
```

---

## 2. Detalle de los Workflows

### 2.1. Backend CI (`ci-backend.yml`)
- **Desencadenadores:** Cambios en `backend/**` y `.github/workflows/ci-backend.yml` sobre ramas `develop` y `main`.
- **Servicios Integrados en Contenedor:**
  - **PostgreSQL 16 (`pgvector/pgvector:pg16`)**: Proporciona soporte nativo para extensiones relacionales y de vectores, con healthchecks `pg_isready` para garantizar que la base de datos esté lista antes del arranque de los tests.
  - **Redis 7 (`redis:7-alpine`)**: Servidor real con healthcheck `redis-cli ping` para validar el funcionamiento del sistema de caché distribuida, Channels y colas de Celery.
- **Comandos Principales:**
  ```bash
  ruff check .
  python manage.py makemigrations --check --dry-run
  pytest --cov --cov-report=xml --cov-report=term
  ```

### 2.2. Frontend CI (`ci-frontend.yml`)
- **Desencadenadores:** Cambios en `frontend/**` y `.github/workflows/ci-frontend.yml` sobre ramas `develop` y `main`.
- **Entorno:** Node.js 22 gestionado con `pnpm` (versión 9/10 congelada con lockfile).
- **Comandos Principales:**
  ```bash
  pnpm install --frozen-lockfile
  pnpm format:check
  pnpm lint
  pnpm typecheck
  pnpm test
  pnpm build
  ```

### 2.3. Docker CI (`ci-docker.yml`)
- **Desencadenadores:** Cambios en `backend/**`, `frontend/**`, `Dockerfile` o `docker-compose.yml`.
- **Validación:** Ejecuta `docker build` sobre el Dockerfile de backend y el Dockerfile multi-stage de frontend para asegurar que las imágenes se construyan de manera reproducible y limpia.

### 2.4. Seguridad SAST y Auditoría (`security.yml`)
- **Desencadenadores:** Eventos `push`, `pull_request` y tarea cron programada semanalmente los lunes a las 03:00 UTC.
- **Herramientas:**
  - **Bandit**: Análisis estático en busca de fallos de seguridad comunes en código Python (inyecciones SQL, uso inseguro de librerías, claves hardcodeadas).
  - **pip-audit**: Escaneo de dependencias en `requirements.txt` contrastadas contra la base de datos de vulnerabilidades PyPA.
  - **pnpm audit**: Escaneo de dependencias frontend para alertar de vulnerabilidades de severidad alta o crítica.

### 2.5. Dependabot (`dependabot.yml`)
- Monitorea y abre PRs automáticas para mantener las librerías al día sin acumular deuda técnica en `backend`, `frontend` y los propios actions de GitHub.

---

## 3. Verificación Local Previa al Despliegue

Todos los pasos del pipeline pueden reproducirse localmente antes de realizar push a `develop`:

```bash
# Verificación de frontend
cd frontend
pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build

# Verificación de backend
docker compose exec -T backend ruff check .
docker compose exec -T backend python manage.py makemigrations --check --dry-run
docker compose exec -T backend pytest tests/test_phase0*.py tests/test_phase11*.py -q

# Verificación de imágenes Docker
docker build -t booksocial-backend:test ./backend
docker build -t booksocial-frontend:test ./frontend
```
