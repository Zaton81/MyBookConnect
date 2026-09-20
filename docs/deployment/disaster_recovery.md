# Plan de Recuperación ante Desastres (Disaster Recovery Plan - DRP)

Este documento establece los protocolos oficiales de recuperación ante incidentes críticos, pérdida de datos, corrupción de infraestructura o fallos de despliegue en MyBookConnect (**Fase 67**).

> [!IMPORTANT]
> **Principio Fundamental de Arquitectura:**
> **Redis no debe ser fuente de verdad.**
> Toda la información persistente reside de forma estricta en PostgreSQL y en el almacenamiento de archivos multimedia (Media). Redis actúa exclusivamente como acelerador de lectura (caché transitoria), capa de sincronización de WebSockets (Django Channels) y broker/backend de tareas en segundo plano. Si Redis se pierde o se borra por completo, la plataforma debe poder continuar operando y regenerarse al 100% a partir de PostgreSQL sin pérdida de datos.

---

## 1. Métricas de Recuperación Objetivo

| Parámetro | Definición | Objetivo MyBookConnect |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | Pérdida máxima de datos admisible en tiempo | $\le 24$ horas (con backups diarios) / $\le 1$ hora (con WAL archiving si está activado) |
| **RTO (Recovery Time Objective)** | Tiempo máximo admisible para restaurar el servicio | $\le 30$ minutos para BD / $\le 15$ minutos para Redis / $\le 45$ minutos para Media |

---

## 2. Runbook 1: Cómo Recuperar la Base de Datos (PostgreSQL)

En caso de corrupción de datos, caída irrecuperable del contenedor o pérdida del volumen de almacenamiento de PostgreSQL:

### Paso 1: Aislar el Tráfico
Detener el tráfico hacia el backend para evitar escrituras inconsistentes durante la restauración:
```bash
docker compose -f docker-compose.prod.yml stop backend celery_worker
```

### Paso 2: Identificar el Backup más Reciente y Validar Integridad SHA-256
Localizar la copia en el volumen persistente `/app/backups/db/` o en el almacenamiento de réplica:
```bash
ls -lt /backups/db/*.sql.gz | head -n 1
```
Verificar que la firma del archivo coincida con su manifest JSON:
```bash
BACKUP_FILE="/backups/db/db_backup_latest.sql.gz"
sha256sum "${BACKUP_FILE}"
cat "${BACKUP_FILE}.manifest.json"
```

### Paso 3: Terminar Conexiones Abiertas y Limpiar Base de Datos
Si la base de datos sigue accesible pero corrupta, terminar sesiones concurrentes para permitir la restauración atómica:
```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER} -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();"
```

### Paso 4: Ejecutar Restauración
#### Opción A (Mediante Script de Producción):
```bash
./scripts/backup/restore_db.sh /backups/db/db_backup_latest.sql.gz
```
#### Opción B (Mediante Comando Django):
```bash
docker compose -f docker-compose.prod.yml run --rm backend python manage.py restore_db /app/backups/db/db_backup_latest.sql.gz
```

### Paso 5: Sincronizar Migraciones y Reanudar Servicios
Si el backup corresponde a una versión anterior, ejecutar migraciones pendientes:
```bash
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml start backend celery_worker
```

---

## 3. Runbook 2: Cómo Recuperar Archivos Multimedia (Media)

En caso de pérdida o corrupción del volumen `backend_media` (portadas de libros, avatares, fotos de autores):

### Paso 1: Restauración desde Backup Local / Tarball
Si se dispone del tarball generado por `backup_media`:
```bash
# Mediante script de producción con validación hash
./scripts/backup/restore_media.sh /backups/media/media_backup_latest.tar.gz

# O mediante comando de gestión Django
docker compose -f docker-compose.prod.yml exec -T backend python manage.py restore_media /app/backups/media/media_backup_latest.tar.gz
```

### Paso 2: Restauración desde Object Storage (S3 / Cloudflare R2 / MinIO)
Si las copias se sincronizan con un bucket remoto seguro:
```bash
aws s3 sync s3://${AWS_STORAGE_BUCKET_NAME}/media/ /app/media/ --delete
```

### Paso 3: Ajuste de Permisos y Propiedad
Asegurar que el usuario no privilegiado del contenedor (`appuser:appgroup`) tenga acceso de lectura y escritura:
```bash
docker compose -f docker-compose.prod.yml exec -T backend chown -R 1000:1000 /app/media
docker compose -f docker-compose.prod.yml exec -T backend chmod -R 755 /app/media
```

---

## 4. Runbook 3: Cómo Regenerar Redis

Dado que **Redis no es fuente de verdad**, un reinicio, fallo o corrupción de Redis no implica pérdida permanente de información del negocio.

### Paso 1: Recrear o Reiniciar el Contenedor de Redis
```bash
# Reiniciar servicio
docker compose -f docker-compose.prod.yml restart cache

# O forzar recreación limpia del contenedor y memoria
docker compose -f docker-compose.prod.yml up -d --force-recreate cache
```

### Paso 2: Validar Conectividad
```bash
docker compose -f docker-compose.prod.yml exec -T cache redis-cli ping
# Respuesta esperada: PONG
```

### Paso 3: Regeneración y Precalentamiento de Caché (`rebuild_cache`)
Para evitar sobrecarga en la base de datos (*cache stampede*) y asegurar tiempos de respuesta óptimos inmediatos:
```bash
docker compose -f docker-compose.prod.yml exec -T backend python manage.py rebuild_cache --limit=50
```
Este comando:
1. Consulta PostgreSQL y calcula las listas de tendencias multi-período (`week`, `month`, `year`, `all`).
2. Precalienta la caché de detalle de los libros más leídos y valorados.
3. Informa las métricas de claves regeneradas y tiempo de respuesta.

---

## 5. Runbook 4: Cómo Desplegar una Versión Anterior (Rollback)

Si una nueva versión en producción presenta errores críticos no detectados:

### Paso 1: Identificar la Versión Estable Previa
Localizar el tag o commit previo verificado en Git o Docker Registry:
```bash
git log --oneline -n 5
# Ejemplo: commit previo 277a16a (v1.0.0)
```

### Paso 2: Revertir Migraciones de Base de Datos (si aplica)
Si la versión defectuosa aplicó migraciones incompatibles hacia atrás, revertirlas antes de cambiar el código:
```bash
# Ver estado de migraciones aplicadas
docker compose -f docker-compose.prod.yml exec -T backend python manage.py showmigrations

# Revertir la app específica a la migración previa
docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate <app_name> <migration_anterior>
```

### Paso 3: Desplegar la Versión Anterior
```bash
# Opción A: Revertir código en el host y reconstruir
git checkout <tag_o_commit_estable>
docker compose -f docker-compose.prod.yml up -d --build

# Opción B: Si se usan imágenes versionadas en registro Docker
sed -i 's/backend:latest/backend:v1.0.0/' docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

### Paso 4: Purgar y Precalentar Caché
```bash
docker compose -f docker-compose.prod.yml exec -T backend python manage.py rebuild_cache --flush-first
```

### Paso 5: Validar Healthcheck
```bash
curl -f http://localhost:8000/api/v1/health/
```

---

## 6. Runbook 5: Cómo Restaurar y Rotar Secretos

Ante sospecha de compromiso, filtración de credenciales o corrupción del archivo `.env`:

### Paso 1: Generar Nuevos Secretos Criptográficos
```bash
# Generar nueva SECRET_KEY Django
NEW_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')

# Generar nueva contraseña PostgreSQL
NEW_DB_PASS=$(python3 -c 'import secrets; print(secrets.token_hex(24))')
```

### Paso 2: Actualizar el Archivo `.env` Seguro
```bash
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${NEW_SECRET_KEY}|" .env
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${NEW_DB_PASS}|" .env
chmod 600 .env
```

### Paso 3: Actualizar la Contraseña en PostgreSQL
```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -c \
  "ALTER USER ${POSTGRES_USER} WITH PASSWORD '${NEW_DB_PASS}';"
```

### Paso 4: Invalidación Forzada de Sesiones y Tokens Comprometidos
Rotar la `SECRET_KEY` invalida automáticamente las firmas criptográficas de sesiones anteriores.
Para revocar inmediatamente todos los tokens JWT emitidos previamente:
```bash
# Purgar sesiones en caché
docker compose -f docker-compose.prod.yml exec -T backend python manage.py shell -c \
  "from django.core.cache import cache; cache.clear()"

# Purgar tokens pendientes de lista negra o invalidar en bloque
docker compose -f docker-compose.prod.yml exec -T backend python manage.py flushexpiredtokens
```

### Paso 5: Reiniciar los Servicios
```bash
docker compose -f docker-compose.prod.yml restart backend celery_worker
```
