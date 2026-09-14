# Guía de Inicio para Desarrolladores

## 1. Requisitos Locales
- **Docker** 24+ y **Docker Compose v2**.
- **Python** 3.12 (opcional, para ejecución fuera de Docker).
- **Node.js** 20+ y `pnpm` (para desarrollo rápido en frontend).

---

## 2. Puesta en Marcha con Docker

1. **Variables de entorno:**
   ```bash
   cp backend/.env.example backend/.env
   cp .env.example .env
   ```
2. **Levantar los servicios:**
   ```bash
   docker compose up -d --build
   ```
3. **Aplicar migraciones:**
   ```bash
   docker compose exec backend python manage.py migrate
   ```
4. **Crear superusuario administrativo:**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

---

## 3. Flujo de Trabajo Diario

### Backend
- Servidor disponible en `http://localhost:8000`.
- Recarga en caliente automática al modificar archivos en `backend/`.
- Ver logs estructurados en tiempo real:
  ```bash
  docker compose logs -f backend
  ```

### Frontend
- Servidor de desarrollo Vite en `http://localhost:5173`.
- HMR (Hot Module Replacement) instantáneo.
- Comprobación de tipos en segundo plano:
  ```bash
  cd frontend
  npm run typecheck
  ```
