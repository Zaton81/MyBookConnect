# Manual de Operaciones y Runbooks de Producción — My Book Social

Este documento es la guía operativa unificada para administradores de sistemas, ingenieros DevOps y personal de guardia ante tareas críticas de mantenimiento, contingencias y operaciones en producción para **My Book Social**.

---

## 1. Procedimiento de Restauración y Disaster Recovery (DRP)

### 1.1. Objetivos del Servicio
- **RPO (Recovery Point Objective):** $\le 24$ horas (respaldos diarios a las 02:00 UTC).
- **RTO (Recovery Time Objective):** $\le 30$ minutos para recuperación total de datos.

### 1.2. Paso a Paso para la Restauración de Base de Datos
En caso de fallo catastrófico, pérdida de datos o corrupción:

1. **Localizar el Respaldo Cifrado:**
   Identifique el último archivo válido en el almacenamiento de backups:
   ```bash
   ls -lat /backups/db/db_backup_*.sql.gz.enc | head -n 1
   ```
2. **Validar la Integridad del Manifiesto SHA-256:**
   ```bash
   BACKUP_NAME="db_backup_YYYYMMDD_HHMMSS"
   sha256sum -c "/backups/db/${BACKUP_NAME}.manifest.json"
   ```
3. **Ejecutar el Script de Restauración Transaccional:**
   ```bash
   cd /opt/mybooksocial
   export BACKUP_ENCRYPTION_KEY="<CLAVE_AES256_CUSTODIADA>"
   ./scripts/backup/restore_db.sh "/backups/db/${BACKUP_NAME}.sql.gz.enc"
   ```
   *Nota:* El script desencripta en memoria, sanitiza posibles sentencias incompatibles (como `transaction_timeout`) y aplica la restauración en modo `--single-transaction`.
4. **Verificar la Integridad del Dominio Post-Restore:**
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend \
     python manage.py verify_restore_integrity
   ```
   *Aceptación:* Debe retornar código 0 confirmando que ratings, usuarios, reseñas y relaciones foráneas son 100% coherentes.

---

## 2. Procedimiento de Rotación de Secretos Críticos

Ante sospecha de compromiso o como parte del ciclo preventivo trimestral:

### 2.1. Rotación de `SECRET_KEY` de Django
1. Generar una clave criptográfica de 64 caracteres:
   ```bash
   NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
   ```
2. Actualizar la variable `SECRET_KEY` en el gestor de secretos o `.env.production`.
3. Reiniciar el servicio backend:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps backend
   ```
   *Impacto:* Las sesiones de Django existentes se invalidan. Los usuarios deberán reautenticarse.

### 2.2. Rotación de Credenciales de PostgreSQL
1. Acceder a la base de datos como superusuario (`postgres`):
   ```bash
   docker compose -f docker-compose.prod.yml exec -T db \
     psql -U postgres -c "ALTER USER mybooksocial_admin WITH PASSWORD 'NUEVO_PASSWORD_SEGURO';"
   ```
2. Actualizar `POSTGRES_PASSWORD` en la configuración del backend y workers de Celery.
3. Reiniciar los servicios dependientes:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker
   ```
4. Validar conectividad mediante la sonda `/health/ready`:
   ```bash
   curl -i https://mybooksocial.com/api/health/ready/
   ```

### 2.3. Rotación de Claves de AWS S3 y Amazon PA-API
1. Generar nuevo par de claves (Access Key / Secret Key) en la consola de AWS IAM.
2. Actualizar `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` y `PAAPI_SECRET_KEY`.
3. Reiniciar backend y Celery.
4. Desactivar y eliminar las claves antiguas en la consola de AWS tras verificar el correcto funcionamiento de subida de avatares y portadas.

---

## 3. Guía de Escalado Horizontal y Operativo

### 3.1. Escalado de Workers Asíncronos de Celery
Si la cola de IA (`ai`), enriquecimiento de libros (`books`) o emails (`emails`) presenta backlog acumulado:

1. **Consultar Backlog de Colas en Redis:**
   ```bash
   docker compose -f docker-compose.prod.yml exec -T cache \
     redis-cli -n 1 llen books
   ```
2. **Desplegar Workers Dedicados por Cola:**
   ```bash
   # Escalar 3 workers dedicados a la cola pesada de libros
   docker compose -f docker-compose.prod.yml up -d --scale celery_worker=3
   ```
   O configurar un worker especializado para la cola de IA con mayor cuota de CPU/memoria en `docker-compose.prod.yml`:
   ```yaml
   celery_ai_worker:
     command: celery -A mybookconnect worker -Q ai --concurrency=2 -l INFO
   ```

### 3.2. Escalado de Instancias Web (Backend Daphne)
1. Escalar el número de contenedores backend:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --scale backend=3
   ```
2. Nginx balancea automáticamente a través del bloque `upstream django_cluster` usando el algoritmo `least_conn`.

---

## 4. Protocolo de Respuesta ante Incidentes P0

```
┌─────────────────┐      Triaje       ┌──────────────────┐     Mitigación     ┌───────────────────┐
│ Alerta Crítica  ├──────────────────►│ Diagnóstico Ráp. ├───────────────────►│ Acción Inmediata   │
│ (Slack/Webhook) │   (< 5 minutos)   │ Sondas / Logs    │    (< 15 minutos)  │ Restart/Rollback  │
└─────────────────┘                   └──────────────────┘                    └───────────────────┘
```

### 4.1. Matriz de Severidad
- **P0 (Crítico):** Caída total del servicio, 5xx > 5%, base de datos inaccesible o vulnerabilidad de seguridad activa con explotación confirmada.
- **P1 (Alto):** Degradación de rendimiento (p95 > 2s), saturación de colas Celery o fallo de proveedor externo (Amazon PA-API).
- **P2 (Medio):** Funcionalidad secundaria no crítica degradada (ej. generación de resúmenes IA).

### 4.2. Flujo de Diagnóstico Rápido
1. **Comprobar Sondas de Salud:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://mybooksocial.com/api/health/live/
   curl -s -o /dev/null -w "%{http_code}\n" https://mybooksocial.com/api/health/ready/
   ```
2. **Inspeccionar Alertas Activas en Tiempo Real:**
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend \
     python manage.py evaluate_system_alerts --format json
   ```
3. **Revisar Logs Estructurados de Backend:**
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=100 -f backend
   ```

### 4.3. Procedimiento de Rollback Inmediato
Si un despliegue reciente introduce un error P0 insalvable:
1. Revertir al commit o tag previo:
   ```bash
   git checkout <TAG_VERSION_ANTERIOR>
   ```
2. Reconstruir y reiniciar contenedores con cero tiempo de inactividad:
   ```bash
   docker compose -f docker-compose.prod.yml build
   docker compose -f docker-compose.prod.yml up -d --no-deps backend frontend
   ```
3. Ejecutar smoke test de producción:
   ```bash
   python scripts/production/smoke_test_prod.py --base-url https://mybooksocial.com
   ```
