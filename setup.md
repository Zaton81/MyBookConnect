# Guía de Instalación y Configuración del Entorno — MyBookConnect

Esta guía contiene las instrucciones necesarias para inicializar, configurar, ejecutar y validar el proyecto **MyBookConnect** desde cero en cualquier estación de trabajo o contenedor de agente.

---

## 1. Requisitos Previos

Asegúrate de contar con las siguientes herramientas instaladas en el sistema host:

- **Docker** (v24.0+) y **Docker Compose** (v2.20+)
- **Git** (v2.40+)
- **Node.js** (v22.x LTS) y gestor de paquetes **pnpm** (v10.x o v9.x)
- **Python** (v3.12.x) *(opcional si se ejecuta todo bajo Docker)*

---

## 2. Configuración Inicial de Variables de Entorno

El proyecto requiere un archivo `.env` en la raíz del repositorio. Existe una plantilla con valores por defecto para desarrollo local:

```bash
# Copiar plantilla de entorno
cp .env.example .env
```

### Variables Críticas en `.env`
- `SECRET_KEY`: Clave de cifrado de sesiones y tokens en Django.
- `DEBUG`: `True` en desarrollo, `False` en producción.
- `POSTGRES_DB`: Nombre de la base de datos (por defecto: `mybookconnect`).
- `POSTGRES_USER`: Usuario administrador de PostgreSQL (por defecto: `postgres`).
- `POSTGRES_PASSWORD`: Contraseña de PostgreSQL.
- `POSTGRES_HOST`: `db` (en Docker Compose) o `localhost` (en local nativo).
- `POSTGRES_PORT`: `5432`.
- `REDIS_URL`: `redis://cache:6379/1` (en Docker Compose) o `redis://localhost:6379/1`.
- `CELERY_BROKER_URL`: `redis://cache:6379/0`.
- `CELERY_RESULT_BACKEND`: `redis://cache:6379/0`.

---

## 3. Arranque del Entorno con Docker (Recomendado)

El entorno principal de desarrollo y testing corre contenerizado con Docker Compose:

```bash
# 1. Construir y levantar servicios en segundo plano
docker compose up -d --build

# 2. Verificar que todos los servicios estén 'healthy' o 'running'
docker compose ps
```

### Servicios Levantados en Desarrollo:
- `booksocial-backend`: Django ASGI (Daphne) en `http://localhost:8000`.
- `booksocial-frontend`: React + Vite + Tailwind en `http://localhost:5173`.
- `booksocial-db`: PostgreSQL 16 con extensión `pgvector` en `localhost:5432`.
- `booksocial-cache`: Redis 7 Alpine en `localhost:6379`.
- `booksocial-celery-worker`: Worker asíncrono de tareas en segundo plano.

---

## 4. Inicialización de la Base de Datos

Una vez que los contenedores estén activos:

```bash
# Aplicar todas las migraciones del ORM
docker compose exec -T backend python manage.py migrate

# Crear un superusuario de administración (interactivo)
docker compose exec backend python manage.py createsuperuser

# (Opcional) Cargar fixtures o datos de prueba si existen
docker compose exec -T backend python manage.py loaddata fixtures/initial_data.json
```

---

## 5. Desarrollo de Frontend (Local Nativo)

Si prefieres ejecutar el frontend en tu máquina host para una recarga rápida con HMR:

```bash
# Acceder al directorio frontend
cd frontend

# Instalar dependencias con pnpm (lockfile congelado)
pnpm install

# Iniciar servidor de desarrollo Vite
pnpm dev
# Acceso en: http://localhost:5173
```

---

## 6. Comandos de Calidad y Validación (Testing y Linters)

Es **obligatorio** verificar que no se introduzcan regresiones antes de realizar cualquier commit.

### 6.1. Backend (Django / Python)
```bash
# Ejecución de análisis estático y estilo con Ruff
docker compose exec -T backend ruff check .

# Verificación de que no existan discrepancias en modelos ORM sin migrar
docker compose exec -T backend python manage.py makemigrations --check --dry-run

# Ejecución de suite de tests unitarios, integración y regresión
# (IMPORTANTE: Nunca ejecutar tests concurrentes sobre la misma base de datos de prueba)
docker compose exec -T backend pytest -q

# Ejecutar tests de una fase específica (ejemplo Fase 13):
docker compose exec -T backend pytest tests/test_phase13_docker_production.py -v
```

### 6.2. Frontend (React / TypeScript)
```bash
# Comprobación de formato con Prettier
pnpm --dir frontend format:check

# Corrección automática de formato
pnpm --dir frontend format

# Análisis de código con ESLint
pnpm --dir frontend lint

# Comprobación estricta de tipos con TypeScript (sin emitir JS)
pnpm --dir frontend typecheck

# Suite de pruebas unitarias y de componentes con Vitest
pnpm --dir frontend test

# Compilación de producción con Vite
pnpm --dir frontend build
```

---

## 7. Despliegue Simulado de Producción

Para validar el comportamiento en la arquitectura de producción (reverse proxy Nginx, aislamiento estricto de redes, graceful shutdown):

```bash
# Compilar y arrancar la infraestructura de producción
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Probar la sonda de liveness del backend
curl -i http://localhost/health/live

# Probar la sonda de readiness del backend (PostgreSQL + Redis)
curl -i http://localhost/health/ready

# Detener los servicios de producción ordenadamente
docker compose -f docker-compose.prod.yml down
```

---

## 8. Solución de Problemas Frecuentes

- **Conflicto de puertos (5432 o 6379 ocupados):**
  Detén servicios locales de PostgreSQL o Redis en tu máquina host (`sudo systemctl stop postgresql redis` o deteniendo los servicios correspondientes en Windows).
- **Base de datos de test bloqueada (`database "test_booksocial" is being accessed by other users`):**
  Asegúrate de que no haya comandos `pytest` corriendo en segundo plano. Si persiste, reinicia el contenedor de base de datos con `docker compose restart db`.
- **Fallo en imports de componentes del frontend:**
  Verifica que las rutas alias en `vite.config.js` y `tsconfig.json` coincidan (`@/*` apunta a `./src/*`).
