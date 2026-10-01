# Guía de Despliegue y Operación en Staging (Beta Cerrada) — MyBookConnect

## 1. Introducción y Propósito

El entorno de **Staging / Pre-producción** constituye la réplica fidedigna de la infraestructura de producción donde se despliega y audita el **Release Candidate (v1.0.0-rc1)** de **MyBookConnect**.

Este entorno tiene como finalidad primordial permitir que los primeros evaluadores y lectores (*Beta Testers*) accedan de manera controlada y segura, asegurando que:
- Los mecanismos de seguridad de cookies, SSL y HSTS funcionen como en producción.
- Los flujos de invitación (`BetaInvitation`), feedback in-app (`BetaFeedback`) y soporte (`SupportTicket`) operen sin fisuras.
- Las dependencias externas (PostgreSQL con `pgvector`, Redis para colas y caché, proveedores de correo) respondan dentro de los presupuestos de latencia (SLA p95 < 200ms).

---

## 2. Requisitos Previos y Preparación

Antes de iniciar el despliegue en el nodo de staging:
1. Asegurar que Docker Engine (>= 24.0) y Docker Compose (>= 2.20) se encuentren instalados y activos.
2. Contar con un archivo `.env.production` específico para staging con credenciales seguras (nunca almacenar en control de versiones).
3. Verificar la coherencia del Release Candidate:
   ```bash
   bash scripts/verify_release.sh
   ```

---

## 3. Despliegue Paso a Paso

### 3.1 Configuración de Variables de Entorno

Copiar la plantilla de producción y ajustar los valores para staging:
```bash
cp .env.production.example .env.staging
```

Configuraciones mínimas requeridas:
```env
DEBUG=0
SECRET_KEY=clave_aleatoria_super_secreta_de_al_menos_50_caracteres_generada_para_staging
DJANGO_ALLOWED_HOSTS=staging.mybookconnect.com localhost 127.0.0.1
ALLOWED_HOSTS=staging.mybookconnect.com localhost 127.0.0.1
CORS_ALLOWED_ORIGINS=https://staging.mybookconnect.com
CSRF_TRUSTED_ORIGINS=https://staging.mybookconnect.com

POSTGRES_DB=mybookconnect_staging
POSTGRES_USER=mbc_staging_user
POSTGRES_PASSWORD=password_seguro_staging
POSTGRES_HOST=db
POSTGRES_PORT=5432

REDIS_HOST=cache
REDIS_PORT=6379
CELERY_BROKER_URL=redis://cache:6379/0

AMAZON_AFFILIATE_TAG=mybooksocial-21
```

### 3.2 Construcción y Arranque de Contenedores

```bash
# 1. Construir las imágenes con optimizaciones de producción
docker compose -f docker-compose.prod.yml build --no-cache

# 2. Levantar los servicios en segundo plano
docker compose -f docker-compose.prod.yml up -d
```

### 3.3 Migraciones y Recolección de Archivos Estáticos

```bash
# Aplicar migraciones pendientes
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate --noinput

# Recolectar archivos estáticos para Nginx
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

---

## 4. Auditoría Pre-Vuelo y Smoke Testing

### 4.1 Auditoría Pre-Despliegue
Ejecutar la suite de comprobaciones automáticas del sistema:
```bash
bash scripts/staging/preflight_staging.sh http://localhost:8000
```
Verifica:
- Conectividad de PostgreSQL y Redis.
- Ausencia de migraciones pendientes.
- Chequeos de seguridad de Django (`check --deploy`).
- Sincronización de versiones SemVer 2.0.0.

### 4.2 Smoke Testing Automatizado
Ejecutar las pruebas sintéticas no destructivas para verificar contratos de API:
```bash
# Ejecución local o contra el dominio de staging
python scripts/staging/smoke_test_staging.py --host http://localhost:8000
# o mediante el wrapper:
bash scripts/staging/smoke_test_staging.sh https://staging.mybookconnect.com
```

Resultados esperados:
- `1. Sonda de Liveness (/health/live)`: `200 OK` con versión `1.0.0-rc1`.
- `2. Sonda de Readiness (/health/ready)`: `200 OK` con base de datos y caché operativas.
- `3. Metadatos de Versión (/api/v1/version/)`: `200 OK` con metadatos SemVer.
- `4. Catálogo Público de Libros (/api/v1/books/)`: `200 OK`.
- `5. Tendencias y Descubrimiento (/api/v1/books/trending/)`: `200 OK`.
- `6. Endpoint de Invitaciones Beta (/api/v1/beta/invitations/verify/)`: `400 Bad Request` esperado ante código inexistente.

---

## 5. Incorporación de Evaluadores (Beta Testers)

### 5.1 Generación de Códigos de Invitación
Para autorizar el acceso a nuevos evaluadores de la beta cerrada, generar invitaciones mediante el panel administrativo (`/admin-panel-ofuscado-mbc/beta/betainvitation/`) o la consola de Django:

```python
# Ejemplo de generación en shell de Django:
from django.utils import timezone
from datetime import timedelta
from beta.models import BetaInvitation

invitation = BetaInvitation.objects.create(
    code="LEER-2026-BETA",
    invited_email="lector.beta@ejemplo.com",
    max_uses=5,
    expires_at=timezone.now() + timedelta(days=30),
    is_active=True
)
print("Invitación creada:", invitation.code)
```

### 5.2 Recolección de Feedback y Soporte
- Los evaluadores pueden reportar incidencias en cualquier momento desde el modal in-app (*Dar Feedback*).
- Los comentarios se centralizan en `/api/v1/beta/admin/feedback/` con categorización automática (`BUG`, `UX`, `PERFORMANCE`, `FEATURE`, `RECOMMENDATIONS`, `CONTENT`, `OTHER`).
- Los tickets de soporte se gestionan en `/api/v1/beta/admin/support/`.

---

## 6. Procedimiento de Rollback Rápido

En caso de detectarse anomalías críticas no tolerables durante las pruebas en staging:

1. Desconectar tráfico entrante o activar modo mantenimiento en Nginx.
2. Detener los contenedores:
   ```bash
   docker compose -f docker-compose.prod.yml down
   ```
3. Restaurar la versión anterior desde el último commit o tag estable.
4. Si se aplicaron migraciones problemáticas, revertirlas:
   ```bash
   docker compose -f docker-compose.prod.yml exec backend python manage.py migrate <app> <migracion_anterior>
   ```
5. Relanzar el entorno y verificar con `smoke_test_staging.sh`.
