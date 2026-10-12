# Manual Operativo de Incidentes de Producción (Incident Runbooks)

Este manual documenta los procedimientos estandarizados de diagnóstico, mitigación inmediata y resolución definitiva para los **5 incidentes operacionales más críticos** en **MyBookConnect** (**Fase B3 — Roadmap v2.0**).

---

## Índice de Runbooks

1. [Runbook 1: Tasa de Errores 5xx Elevada (`high_5xx_rate`)](#runbook-1-tasa-de-errores-5xx-elevada-high_5xx_rate)
2. [Runbook 2: Inaccesibilidad o Latencia Crítica en PostgreSQL (`db_unavailable`)](#runbook-2-inaccesibilidad-o-latencia-crítica-en-postgresql-db_unavailable)
3. [Runbook 3: Caída o Saturación de Memoria en Redis (`redis_unavailable`)](#runbook-3-caída-o-saturación-de-memoria-en-redis-redis_unavailable)
4. [Runbook 4: Saturación de Tareas en Colas Celery (`celery_backlog`)](#runbook-4-saturación-de-tareas-en-colas-celery-celery_backlog)
5. [Runbook 5: Saturación de Almacenamiento en Disco (`disk_usage_high`)](#runbook-5-saturación-de-almacenamiento-en-disco-disk_usage_high)

---

## Runbook 1: Tasa de Errores 5xx Elevada (`high_5xx_rate`)

### Umbral de Alerta
- Tasa de errores 5xx $> 1.0\%$ sobre el tráfico total de peticiones (severidad: **CRITICAL**).

### Diagnóstico Rápido
1. Consultar el estado del endpoint de métricas y observabilidad:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend python manage.py evaluate_system_alerts --json
   ```
2. Inspeccionar los logs estructurados JSON en búsqueda de excepciones sin capturar:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=100 backend | grep '"status":50'
   ```
3. Verificar eventos y trazas de error en el panel de Sentry configurado.

### Acciones de Mitigación Inmediata
1. Si los errores corresponden a un despliegue reciente con fallo de regresión:
   - Ejecutar procedimiento de Rollback documentado en `docs/deployment/disaster_recovery.md` (Sección 5).
2. Si los errores provienen de saturación de hilos Daphne por peticiones lentas:
   - Reiniciar ordenadamente los procesos backend:
     ```bash
     docker compose -f docker-compose.prod.yml restart backend
     ```
3. Si los errores son causados por ataques o tráfico abusivo en endpoints específicos:
   - Aplicar rate limiting agresivo temporal en Nginx o bloquear IPs agresoras mediante `limit_req_zone`.

---

## Runbook 2: Inaccesibilidad o Latencia Crítica en PostgreSQL (`db_unavailable`)

### Umbral de Alerta
- La sonda `/health/ready` responde `503 Service Unavailable` o la latencia de DB es $< 0$ (severidad: **CRITICAL**).

### Diagnóstico Rápido
1. Comprobar el estado del contenedor de base de datos:
   ```bash
   docker compose -f docker-compose.prod.yml ps db
   ```
2. Inspeccionar conexiones concurrentes y bloqueos en PostgreSQL:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
     "SELECT pid, state, query, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start ASC;"
   ```

### Acciones de Mitigación Inmediata
1. Si existen transacciones colgadas bloqueando tablas críticas:
   - Cancelar consultas bloqueadoras:
     ```bash
     docker compose -f docker-compose.prod.yml exec -T db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c \
       "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <PID_BLOQUEADOR>;"
     ```
2. Si el servicio PostgreSQL se detuvo por falta de memoria o reinicio inesperado:
   - Reiniciar el contenedor:
     ```bash
     docker compose -f docker-compose.prod.yml restart db
     ```
3. Si la base de datos presenta corrupción física irrecuperable:
   - Ejecutar el procedimiento de restauración desde backup cifrado (`./scripts/backup/restore_db.sh`).

---

## Runbook 3: Caída o Saturación de Memoria en Redis (`redis_unavailable`)

### Umbral de Alerta
- Redis no responde a `ping` o el uso de memoria excede el presupuesto (severidad: **CRITICAL**).

> [!IMPORTANT]
> **Redis no es fuente de verdad.** Su caída temporal no implica pérdida permanente de información de negocio (usuarios, libros, reseñas y mensajes residen exclusivamente en PostgreSQL).

### Diagnóstico Rápido
1. Probar conectividad con Redis:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T cache redis-cli ping
   ```
2. Consultar el uso de memoria y política de desalojo:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T cache redis-cli info memory
   ```

### Acciones de Mitigación Inmediata
1. Reiniciar el contenedor de Redis para forzar liberación limpia:
   ```bash
   docker compose -f docker-compose.prod.yml restart cache
   ```
2. Tras recuperar la conectividad, precalentar la caché de catálogos y tendencias:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend python manage.py rebuild_cache --limit=50
   ```

---

## Runbook 4: Saturación de Tareas en Colas Celery (`celery_backlog`)

### Umbral de Alerta
- Tareas acumuladas en colas de Celery $> 100$ (severidad: **WARNING**).

### Diagnóstico Rápido
1. Inspeccionar la profundidad de las colas en Redis:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T cache redis-cli llen celery
   docker compose -f docker-compose.prod.yml exec -T cache redis-cli llen books
   docker compose -f docker-compose.prod.yml exec -T cache redis-cli llen emails
   ```
2. Inspeccionar los logs del worker para detectar tareas en bucle o bloqueadas en I/O:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=100 celery_worker
   ```

### Acciones de Mitigación Inmediata
1. Si las tareas se procesan normalmente pero a menor ritmo que la demanda de tráfico:
   - Escalar horizontalmente el número de workers:
     ```bash
     docker compose -f docker-compose.prod.yml up -d --scale celery_worker=2
     ```
2. Si un lote masivo de tareas defectuosas está bloqueando la cola:
   - Reiniciar el servicio Celery para abortar tareas colgadas:
     ```bash
     docker compose -f docker-compose.prod.yml restart celery_worker
     ```

---

## Runbook 5: Saturación de Almacenamiento en Disco (`disk_usage_high`)

### Umbral de Alerta
- Uso de almacenamiento en disco $> 85.0\%$ (severidad: **WARNING**).

### Diagnóstico Rápido
1. Comprobar uso de las particiones del sistema:
   ```bash
   df -h
   ```
2. Identificar los directorios más voluminosos:
   ```bash
   du -sh ./backups/* ./backend/media/* /var/lib/docker/volumes/* 2>/dev/null | sort -hr | head -n 10
   ```

### Acciones de Mitigación Inmediata
1. Purgar copias de seguridad que excedan los días de retención:
   ```bash
   find ./backups/db -type f -name "db_backup_*.sql.gz*" -mtime +7 -delete
   find ./backups/media -type f -name "media_backup_*.tar.gz*" -mtime +30 -delete
   ```
2. Limpiar capas de imágenes, contenedores detenidos y caché de build de Docker:
   ```bash
   docker system prune -f
   ```
3. Rotar o truncar logs de contenedores si no están gestionados por `logrotate`.
