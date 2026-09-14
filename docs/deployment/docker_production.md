# Guía de Despliegue en Producción con Docker

## 1. Arquitectura de Despliegue
En producción, MyBookConnect se orquesta mediante `docker-compose.prod.yml`:
- **Nginx:** Reverse proxy externo expuesto a los puertos 80 y 443.
- **Backend (WSGI):** Gunicorn sirviendo la API REST sobre el puerto interno 8000.
- **Backend (ASGI):** Daphne gestionando WebSockets sobre `/ws/`.
- **Celery Worker:** Procesamiento asíncrono de enriquecimiento de libros.
- **PostgreSQL 16 & Redis 7:** Confinados exclusivamente a la red bridge interna `mybookconnect_default`.

---

## 2. Puesta en Marcha en Producción

### 1. Preparación de Variables de Entorno
Crear un archivo `.env` seguro sin contraseñas por defecto ni claves de desarrollo:
```bash
DEBUG=False
SECRET_KEY=clave_criptografica_muy_larga_y_aleatoria
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
POSTGRES_DB=mybookconnect_prod
POSTGRES_USER=mbc_admin
POSTGRES_PASSWORD=password_super_seguro_generado
REDIS_URL=redis://cache:6379/0
```

### 2. Construcción y Despliegue
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build
```

### 3. Migraciones y Recolección de Estáticos
```bash
docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
```
