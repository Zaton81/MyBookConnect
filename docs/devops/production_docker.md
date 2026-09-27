# Arquitectura de Producción y Dockerización — MyBookConnect

## 1. Visión General de la Arquitectura

La infraestructura de producción de MyBookConnect está diseñada siguiendo los principios de **mínimo privilegio**, **aislamiento de red por capas** y **alta disponibilidad** definidos en la **Fase 13 de RoadmapV2.md**.

El sistema desacopla estrictamente los componentes accesibles desde Internet de los almacenes de datos y procesos en segundo plano, garantizando que un fallo en un componente no exponga ni comprometa el resto del ecosistema.

```text
[ Internet / Clientes Públicos ]
              │ (HTTP :80 / HTTPS :443)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      REVERSE PROXY (Nginx)                      │
│                    Servicio: 'frontend'                         │
│  - Expone puertos 80/443 hacia el host                          │
│  - Red: 'frontend_net'                                          │
│  - Sirve SPA compilada (/usr/share/nginx/html)                  │
│  - Sirve /static/ y /media/ en modo solo lectura                │
│  - Proxy inverso para /api/ y /ws/ hacia backend                │
│  - Proxy de sondas /health/live y /health/ready                 │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Red bridge: frontend_net
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                 BACKEND ASGI / WS (Daphne / Django)             │
│                    Servicio: 'backend'                          │
│  - Expone puerto interno 8000 (sin mapeo de puertos al host)    │
│  - Redes: 'frontend_net' y 'backend_net'                        │
│  - Graceful shutdown: SIGTERM, 30s grace period                 │
│  - Healthchecks: /health/live y /health/ready                   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Red interna privada: backend_net (internal: true)
                ┌────────────────┴────────────────┐
                ▼                                 ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│        CELERY WORKER         │   │         DATA STORES          │
│   Servicio: 'celery_worker'  │   │                              │
│  - Procesamiento asíncrono   │   │  PostgreSQL 16 (pgvector)    │
│  - Red: 'backend_net'        │   │  - Servicio: 'db'            │
│  - Graceful shutdown:        │   │  - Puerto 5432 (no expuesto) │
│    SIGTERM, 60s grace period │   │                              │
│                              │   │  Redis 7 Alpine              │
│                              │   │  - Servicio: 'cache'         │
│                              │   │  - Puerto 6379 (no expuesto) │
└──────────────────────────────┘   └──────────────────────────────┘
```

---

## 2. Aislamiento de Redes y Seguridad de Puertos

### 2.1. Redes Docker
En [docker-compose.prod.yml](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docker-compose.prod.yml) se declaran dos redes bridge con propósitos disjuntos:

1. `frontend_net`: Red pública compartida exclusivamente entre el reverse proxy Nginx (`frontend`) y el servidor de aplicaciones (`backend`).
2. `backend_net`: Red privada con flag `internal: true`. Conecta el `backend`, el `celery_worker`, la base de datos `db` y la caché `cache`.
   - **Regla estricta:** El contenedor Nginx **no pertenece** a `backend_net`, impidiendo cualquier vector de conexión directa desde el exterior hacia PostgreSQL o Redis.

### 2.2. Política de Exposición de Puertos
- **Internet / Host:** Únicamente el servicio `frontend` mapea puertos al exterior (`80:80` / `443:443`).
- **Backend Django:** No mapea puertos al host (`ports` omitido). Utiliza `expose: ["8000"]` para ser accesible solo por Nginx dentro de `frontend_net`.
- **PostgreSQL y Redis:** No mapean puertos al host (`ports` omitido). Su conectividad queda restringida exclusivamente a contenedores dentro de `backend_net`.

---

## 3. Sondas Canónicas de Salud (Healthchecks)

Para integrarse de forma estándar con orquestadores (Docker Swarm, Kubernetes, AWS ECS) y con el balanceador de carga, se exponen dos sondas diferenciadas:

### 3.1. Sonda de Liveness (`/health/live`)
- **Propósito:** Comprobar que el proceso ASGI (Daphne) y el runtime de Django están vivos y respondiendo peticiones HTTP.
- **Comportamiento:** Responde `200 OK` de forma inmediata con `{"status": "healthy", "process": "alive", "version": "..."}`.
- **Aislamiento:** **No ejecuta consultas a PostgreSQL ni a Redis**. Si la base de datos o la caché experimentan una caída temporal, la sonda de liveness permanece en `200 OK` para evitar que el orquestador reinicie en bucle (*crash loop*) el contenedor web innecesariamente.

### 3.2. Sonda de Readiness (`/health/ready`)
- **Propósito:** Comprobar si la aplicación está lista para recibir y procesar tráfico de usuarios reales.
- **Comportamiento:**
  - Ejecuta un `SELECT 1;` sobre PostgreSQL y una operación de set/get con TTL corto sobre Redis.
  - Si ambas dependencias responden: retorna `200 OK` con `{"status": "ready", "services": {"database": "ready", "cache": "ready"}}`.
  - Si alguna dependencia falla: retorna `503 SERVICE UNAVAILABLE` con `{"status": "not_ready", "services": {"database": "unhealthy: ...", ...}}`.
- **Uso en Compose:** El healthcheck del contenedor `backend` en Compose utiliza esta sonda:
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8000/health/ready || exit 1"]
    interval: 15s
    timeout: 5s
    retries: 3
    start_period: 15s
  ```

---

## 4. Estrategia de Graceful Shutdown

Durante actualizaciones y despliegues *zero-downtime*, es imprescindible no abortar abruptamente peticiones HTTP en vuelo ni tareas asíncronas de Celery (como generación de embeddings o indexación de lecturas).

| Servicio | Señal de Parada (`stop_signal`) | Periodo de Gracia (`stop_grace_period`) | Comportamiento |
| :--- | :--- | :--- | :--- |
| `frontend` (Nginx) | `SIGQUIT` | 10s | Cierra el socket de escucha y finaliza la entrega de respuestas a clientes conectados. |
| `backend` (Daphne) | `SIGTERM` | 30s | Deja de aceptar nuevas conexiones HTTP/WS y drena las solicitudes activas antes de finalizar el proceso. |
| `celery_worker` | `SIGTERM` | 60s | Warm shutdown: no toma nuevas tareas de la cola y permite que las tareas en ejecución concluyan sin corrupción de datos. |

---

## 5. Volúmenes Persistentes y Copias de Seguridad

En `docker-compose.prod.yml` todos los volúmenes están explícitamente nombrados y desacoplados del ciclo de vida de los contenedores efímeros:

1. `db_prod_data` (`/var/lib/postgresql/data`): Persistencia de los esquemas, tablas e índices pgvector de PostgreSQL 16.
2. `backend_media` (`/app/media`): Almacenamiento de avatares y portadas de libros subidos por los usuarios. Nginx lo monta en modo solo lectura (`ro`) para servirlos con alta velocidad y cabeceras `Cache-Control: public, no-transform`.
3. `backend_static` (`/app/staticfiles`): Archivos estáticos de Django (`collectstatic`). Nginx los monta en modo solo lectura (`ro`) bajo `/django_static/` con caché inmutable de 1 año.
4. `backups_data` (`/app/backups`): Directorio persistente de almacenamiento de volcados comprimidos generados por los scripts de respaldo.

### 5.1. Ejecución de Backups de Base de Datos
Para generar una copia de seguridad manual o programada (vía cron en el host):
```bash
# Ejecución del script de backup con integridad SHA-256 y rotación de retención
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres -d mybookconnect \
  --clean --if-exists --no-owner --no-privileges | gzip -9 > /backups/db/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```
O ejecutando el script canónico:
```bash
./scripts/backup/backup_db.sh
```

---

## 6. Comandos Operativos de Producción

### 6.1. Compilación y Arranque
```bash
# Compilar imágenes sin caché y levantar en segundo plano
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

### 6.2. Verificación de Estado y Healthchecks
```bash
# Comprobar el estado de salud de todos los contenedores
docker compose -f docker-compose.prod.yml ps

# Probar la sonda de liveness
curl -I http://localhost/health/live

# Probar la sonda de readiness
curl -i http://localhost/health/ready
```

### 6.3. Recolección de Archivos Estáticos y Migraciones
```bash
# Aplicar migraciones pendientes
docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput

# Recolectar estáticos para Nginx
docker compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
```
