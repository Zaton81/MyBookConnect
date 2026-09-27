# Estrategia de Copias de Seguridad y Plan de Recuperación ante Desastres (Disaster Recovery) — MyBookConnect

## 1. Visión General y Métricas de Continuidad (RPO / RTO)

La política de copias de seguridad y recuperación de MyBookConnect está diseñada conforme a la **Fase 15 de RoadmapV2.md** (Sección 20) para garantizar la protección de la información de los usuarios, la resiliencia operativa y la restauración determinista del servicio ante cualquier eventualidad catastrófica.

### 1.1. Objetivos Formales de Recuperación (SLAs)

| Métrica | Definición | Objetivo Máximo | Mecanismo |
| :--- | :--- | :--- | :--- |
| **RPO** *(Recovery Point Objective)* | Máxima pérdida de datos transaccionales admisible entre el desastre y el último respaldo. | **24 horas** | Volcados completos diarios de PostgreSQL a las 02:00 UTC con retención local y en la nube. |
| **RTO** *(Recovery Time Objective)* | Tiempo máximo admisible para restablecer el servicio completo en una infraestructura nueva. | **4 horas** | Aprovisionamiento con Docker Compose, restauración automatizada con `restore_db.sh` y verificación de integridad. |

---

## 2. Política de Respaldo de PostgreSQL (20.1)

### 2.1. Frecuencia y Programación
- **Periodicidad:** Diaria, ejecutada a las 02:00 UTC (mediante cron del sistema host o tarea programada).
- **Herramienta:** `pg_dump` con formato texto SQL comprimido en gzip de máxima compresión (`gzip -9`).
- **Opciones de volcado:** `--clean --if-exists --no-owner --no-privileges` para garantizar que el archivo pueda ser restaurado en cualquier clúster sin conflictos de usuarios del sistema.

### 2.2. Cifrado en Reposo (AES-256-CBC)
Si se configura la variable de entorno `BACKUP_ENCRYPTION_KEY` o `BACKUP_PASSPHRASE`:
- El volcado se cifra con **AES-256-CBC** utilizando sal aleatoria y derivación de clave por PBKDF2 (`openssl enc -aes-256-cbc -salt -pbkdf2`).
- El archivo resultante adopta la extensión `.sql.gz.enc`.
- Se genera un manifiesto criptográfico `.manifest.json` con la firma SHA-256 calculada **sobre el archivo cifrado final**.

### 2.3. Manifiesto de Integridad SHA-256
Cada archivo de respaldo genera un manifiesto JSON anexo:
```json
{
  "version": "1.1",
  "type": "database",
  "format": "pg_dump_gzip_aes256",
  "database": "mybookconnect",
  "filename": "db_backup_mybookconnect_20260927_020000.sql.gz.enc",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 1542012,
  "encrypted": true,
  "cipher": "aes-256-cbc",
  "created_at": "2026-09-27T02:00:00Z",
  "retention_days": 7
}
```

### 2.4. Política de Retención y Almacenamiento Externo
- **Almacenamiento Local:** 7 días de retención en el volumen Docker `backups_data` (`/app/backups/db/`).
- **Almacenamiento en la Nube (S3 / MinIO / GCS):** Replicación opcional mediante `aws s3 cp` al bucket definido en `BACKUP_S3_BUCKET` o `AWS_STORAGE_BUCKET_NAME` con ciclo de vida (retención de 30 días y archivado en Glacier).

---

## 3. Política de Respaldo de Archivos Multimedia (20.2)

- **Frecuencia:** Diaria a las 03:00 UTC.
- **Ruta de origen:** Directorio de medios `/app/media/` (montado en el volumen `backend_media`).
- **Empaquetado:** Archivo tarball comprimido `tar.gz` independiente de la base de datos.
- **Cifrado y Verificación:** Compatible con cifrado AES-256 y manifest SHA-256 idéntico al de base de datos.
- **Retención:** 30 días de retención local y remota.

---

## 4. Principio de Aislamiento: Redis NO es Fuente de Verdad (20.3)

MyBookConnect opera bajo el principio estricto de que **Redis es un almacén volátil transitorio**:

1. **Caché L2 (`safe_cache_get` / `safe_cache_set`):**
   - Ante la caída o reinicio de Redis (`FLUSHALL`), la aplicación ejecuta un fallback automático hacia PostgreSQL sin interrupción del servicio ni pérdida de información.
2. **Tokens de Autenticación (JWT):**
   - Los tokens de acceso y refresco se validan criptográficamente con la firma de la clave `SECRET_KEY` configurada en Django, y las entidades de usuario se leen de la base de datos relacional.
3. **WebSockets (Django Channels):**
   - Redis actúa como layer de mensajería efímero. Si se reinicia, las conexiones activas se reconectan automáticamente mediante el mecanismo de backoff exponencial implementado en el frontend.

---

## 5. Procedimiento Automatizado de Prueba de Restauración (20.4)

Un respaldo cuya restauración no ha sido verificada carece de validez operativa.

El script [scripts/backup/test_restore_cycle.sh](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/scripts/backup/test_restore_cycle.sh) implementa el ciclo de validación integral:

```text
1. backup       -> Generación de volcado y cálculo de hash SHA-256.
2. restore      -> Creación de base de datos aislada 'mbc_verify_restore_...' y restauración transaccional.
3. migrate/check-> Verificación de integridad estructural del esquema relacional y migraciones.
4. smoke tests  -> Consultas de validación sobre tablas críticas ('users_user', 'books_book').
5. cleanup      -> Destrucción de la base de datos temporal y purga de archivos efímeros.
```

### Ejecución del Ciclo de Prueba:
```bash
./scripts/backup/test_restore_cycle.sh
```

---

## 6. Runbook de Recuperación ante Desastres (Disaster Recovery Step-by-Step)

En caso de fallo total del servidor, hardware o proveedor de nube:

### Paso 1: Aprovisionar Nueva Instancia y Repositorio
```bash
# 1. Clonar el repositorio en la nueva máquina
git clone https://github.com/Zaton81/MyBookConnect.git
cd MyBookConnect
git checkout develop

# 2. Configurar variables de entorno con las claves maestras
cp .env.example .env
# Configurar SECRET_KEY, POSTGRES_PASSWORD y BACKUP_ENCRYPTION_KEY en .env
```

### Paso 2: Descargar Respaldo Cifrado desde Almacenamiento Remoto
```bash
# Crear directorio de respaldos
mkdir -p /backups/db /backups/media

# Descargar el último respaldo validado desde S3
aws s3 cp s3://mybookconnect-backups/backups/db/db_backup_latest.sql.gz.enc /backups/db/
aws s3 cp s3://mybookconnect-backups/backups/db/db_backup_latest.sql.gz.enc.manifest.json /backups/db/
aws s3 cp s3://mybookconnect-backups/backups/media/media_backup_latest.tar.gz.enc /backups/media/
aws s3 cp s3://mybookconnect-backups/backups/media/media_backup_latest.tar.gz.enc.manifest.json /backups/media/
```

### Paso 3: Levantar Contenedores de Base de Datos y Caché
```bash
# Iniciar servicios de almacenamiento
docker compose -f docker-compose.prod.yml up -d db cache
```

### Paso 4: Restaurar Base de Datos PostgreSQL con Descifrado
```bash
# Ejecutar restauración con verificación de hash SHA-256 y descifrado AES-256
./scripts/backup/restore_db.sh /backups/db/db_backup_latest.sql.gz.enc
```

### Paso 5: Restaurar Archivos Multimedia
```bash
# Restaurar archivos de usuario en el volumen backend_media
./scripts/backup/restore_media.sh /backups/media/media_backup_latest.tar.gz.enc
```

### Paso 6: Levantar Backend, Celery y Reverse Proxy Nginx
```bash
# Levantar la plataforma completa en producción
docker compose -f docker-compose.prod.yml up -d

# Verificar estado de salud (Liveness y Readiness)
curl -i http://localhost/health/live
curl -i http://localhost/health/ready
```
