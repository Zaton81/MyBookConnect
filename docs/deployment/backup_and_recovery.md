# Guía de Copias de Seguridad (Backups) y Recuperación ante Desastres

Esta guía documenta la arquitectura, automatización, políticas de retención y procedimientos de validación y restauración de copias de seguridad de MyBookConnect (**Fase 66**).

> [!IMPORTANT]
> **Regla de oro de fiabilidad:** *Un backup que nunca se ha restaurado no se considera validado.*
> Todo procedimiento de copia de seguridad debe contar con simulacros periódicos de restauración (*drills*) para comprobar la integridad de datos y archivos.

---

## 1. Arquitectura de Backups

La estrategia de respaldo de MyBookConnect cubre dos capas críticas:

| Capa | Origen de Datos | Formato de Salida | Mecanismo de Verificación |
| :--- | :--- | :--- | :--- |
| **Base de Datos (PostgreSQL)** | Base de datos relacional `mybookconnect` | `.sql.gz` (`pg_dump` con gzip) o `.json.gz` (Django) | Firma criptográfica SHA-256 + Manifest JSON |
| **Archivos Multimedia (Media)** | `/app/media` (portadas de libros, avatares) | `.tar.gz` | Firma SHA-256 global + Hashes individuales por archivo |

---

## 2. Políticas de Retención

Las políticas de retención eliminan automáticamente las copias que superen el umbral de vida útil para evitar saturación del almacenamiento, garantizando siempre la permanencia de al menos la copia más reciente:

- **Base de Datos (`BACKUP_RETENTION_DAYS`)**: 7 días (configurable vía entorno).
- **Archivos Multimedia (`MEDIA_BACKUP_RETENTION_DAYS`)**: 30 días (configurable vía entorno).

---

## 3. Ejecución Mediante Comandos Django

Los comandos de gestión integrados permiten programar backups y restauraciones desde tareas Celery, pipelines CI/CD o la terminal del contenedor:

### 3.1 Backup de Base de Datos
```bash
# Generar copia diaria estándar en backups/db/
python manage.py backup_db

# Especificar directorio de salida y días de retención
python manage.py backup_db --output-dir=/app/backups/db --retention-days=14

# Forzar serialización interna Django
python manage.py backup_db --force-django-dump
```

### 3.2 Restauración de Base de Datos
```bash
# Restauración con verificación obligatoria de firma SHA-256
python manage.py restore_db /app/backups/db/db_backup_mybookconnect_20260920_120000.sql.gz

# Restauración saltando verificación (solo para emergencias)
python manage.py restore_db /app/backups/db/db_backup_mybookconnect_20260920_120000.sql.gz --no-verify
```

### 3.3 Backup de Archivos Multimedia
```bash
# Empaquetar media en backups/media/
python manage.py backup_media

# Sincronización con almacenamiento de objetos S3/R2/MinIO
python manage.py backup_media --s3-sync
```

### 3.4 Restauración de Archivos Multimedia
```bash
# Restaurar media validando integridad archivo por archivo
python manage.py restore_media /app/backups/media/media_backup_20260920_120000.tar.gz
```

---

## 4. Scripts de Producción (Host / Cron)

En servidores Linux de producción, los scripts ubicados en `scripts/backup/` pueden programarse mediante `cron` o `systemd timers`:

### 4.1 Permisos de Ejecución
```bash
chmod +x scripts/backup/*.sh
```

### 4.2 Configuración Cron Recomendada (`/etc/cron.d/mybookconnect-backups`)
```cron
# Backup diario de PostgreSQL a las 02:00 UTC
0 2 * * * root cd /opt/mybookconnect && ./scripts/backup/backup_db.sh >> /var/log/mybookconnect/backup_db.log 2>&1

# Backup semanal de Media los domingos a las 03:00 UTC
0 3 * * 0 root cd /opt/mybookconnect && ./scripts/backup/backup_media.sh >> /var/log/mybookconnect/backup_media.log 2>&1
```

---

## 5. Simulacro de Restauración (*Restoration Drill*)

Para validar que un backup es plenamente funcional y consistente, seguir estos pasos:

1. **Inspeccionar el Manifest Criptográfico:**
   ```bash
   cat /app/backups/db/db_backup_*.manifest.json
   ```
2. **Validar la Firma SHA-256:**
   ```bash
   sha256sum -c <(grep sha256 db_backup_*.manifest.json | awk '{print $2, "db_backup_*.sql.gz"}')
   ```
3. **Ejecutar Restauración:**
   ```bash
   python manage.py restore_db /app/backups/db/db_backup_latest.sql.gz
   python manage.py restore_media /app/backups/media/media_backup_latest.tar.gz
   ```
4. **Comprobación de Integridad de Modelos:**
   ```bash
   python manage.py shell -c "from books.models import Book, Review; from users.models import User; print(f'Usuarios: {User.objects.count()}, Libros: {Book.objects.count()}, Reseñas: {Review.objects.count()}')"
   ```

---

## 6. Almacenamiento Remoto en S3 / MinIO / Cloudflare R2

Para producción, se recomienda configurar un bucket externo seguro:
```bash
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_STORAGE_BUCKET_NAME=mybookconnect-backups
AWS_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
```

Los scripts suben automáticamente los volcados y sus manifests criptográficos al bucket cuando están configuradas las credenciales.
