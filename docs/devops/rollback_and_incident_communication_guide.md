# Guía Operativa de Rollback y Comunicación de Incidentes — My Book Social

Este documento establece el **protocolo formal y verificable de reversión (rollback)** de despliegues y la **estrategia de comunicación de incidentes** para la plataforma **My Book Social** (`mybooksocial.com`), en cumplimiento de la **Fase E2 (Roadmap v2.0 Bloque E)**.

---

## 1. Alcance y Criterios de Activación

Un procedimiento de **rollback** revierte la plataforma al estado inmediatamente anterior validado y estable. No es un procedimiento rutinario, sino un mecanismo de contención crítica ante fallos graves en pre-producción o producción.

### Umbrales Críticos de Activación (SLA Breach)

| Métrica / Síntoma | Condición de Disparo | Severidad | Acción Requerida |
| :--- | :--- | :--- | :--- |
| **Tasa de Errores HTTP 5xx** | $> 1.0\%$ durante más de 3 minutos consecutivos | **SEV-1** | Rollback inmediato de imagen/código |
| **Latencia p95 de API** | $> 2000\text{ ms}$ durante más de 5 minutos sostenidos | **SEV-1 / SEV-2** | Rollback o escalado reactivo |
| **Sonda de Readiness (`/health/ready`)** | Retorno continuo de `503 Service Unavailable` por fallo de DB o Redis | **SEV-1** | Rollback o failover de base de datos |
| **Fallo en Migraciones Django** | Inconsistencia de esquema o error de migración irreversible | **SEV-1** | Rollback de base de datos / Restore snapshot |
| **Vulnerabilidad Crítica en Caliente** | Detección de bypass de auth, IDOR o fuga de datos privados | **SEV-1** | Rollback inmediato o activación de feature flag de mantenimiento |

---

## 2. Clasificación de Severidad y Cadena de Mando

- **SEV-1 (Catastrófico / Crítico):** Plataforma completamente inaccesible o pérdida/corrupción potencial de datos. Tiempo objetivo de mitigación (TTR): $< 15\text{ minutos}$.
- **SEV-2 (Mayor / Parcial):** Funcionalidad crítica degradada (ej. login fallido, feed inaccesible, incapacidad de guardar reseñas). TTR: $< 45\text{ minutos}$.
- **SEV-3 (Menor):** Incidencia cosmética o funcionalidad no crítica degradada (ej. recomendaciones diferidas, métricas en cola). TTR: $< 4\text{ horas}$.

### Roles Durante el Incidente

1. **Incident Commander (IC):** Coordina las decisiones, aprueba formalmente la orden de rollback y mantiene el cronograma del incidente.
2. **Technical Runbook Executor (Ops/Backend Lead):** Ejecuta paso a paso los comandos de infraestructura, base de datos y contenedores.
3. **Communications Lead:** Redacta y despacha los avisos a usuarios, autores y canales públicos según las plantillas de este documento.

---

## 3. Procedimiento de Rollback Paso a Paso

### Fase 1: Congelación y Notificación

1. Declarar el inicio del incidente y notificar internamente:
   ```bash
   # Registrar inicio de intervención en el log de auditoría
   docker compose -f docker-compose.prod.yml exec -T backend python manage.py log_incident --severity=SEV-1 --reason="Rollback iniciado tras despliegue fallido"
   ```
2. Si el fallo corrompe escrituras de usuarios, conmutar temporalmente la plataforma a modo mantenimiento con feature flags:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend python manage.py set_system_flag --flag=PUBLIC_REGISTRATION_ENABLED --value=false
   ```

### Fase 2: Reversión de Contenedores y Código de Aplicación

1. Identificar la imagen o tag git previo estable:
   ```bash
   export PREVIOUS_RELEASE_TAG="1.0.0" # O hash git previo verificado
   ```
2. Re-desplegar los servicios backend y frontend con la versión previa:
   ```bash
   # Re-etiquetar o apuntar a la imagen anterior en compose
   docker compose -f docker-compose.prod.yml stop backend celery_worker
   docker compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker
   ```

### Fase 3: Reversión de Base de Datos y Migraciones

La estrategia depende de si el despliegue contenía migraciones hacia adelante reversibles o destructivas:

#### Opción A: Migración Reversible (Backward Compatible)
Si la migración previa fue aditiva (ej. nuevas columnas nulables o índices):
```bash
# Revertir la migración específica al nodo anterior
docker compose -f docker-compose.prod.yml exec -T backend python manage.py migrate <app_name> <migration_number_anterior>
```

#### Opción B: Restauración Completa de Snapshot (Desastre / Inconsistencia Irreversible)
Si la base de datos sufrió modificaciones destructivas de esquema o datos:
```bash
# 1. Detener escrituras deteniendo el backend
docker compose -f docker-compose.prod.yml stop backend celery_worker

# 2. Ejecutar restauración del backup pre-despliegue
./scripts/backup/restore_db.sh /backups/postgres/pre_deploy_snapshot.sql.gz.enc

# 3. Validar integridad de las tablas
docker compose -f docker-compose.prod.yml exec -T backend python manage.py verify_restore_integrity

# 4. Reanudar servicios
docker compose -f docker-compose.prod.yml start backend celery_worker
```

### Fase 4: Purgado de Caché y Capa de Conexiones

Para evitar que datos residuales corruptos permanezcan en memoria:
```bash
# Purgar caché de Redis de la aplicación respetando colas Celery
docker compose -f docker-compose.prod.yml exec -T cache redis-cli -n 1 FLUSHDB
```

### Fase 5: Verificación Post-Rollback (Sanity & Smoke)

1. Comprobar sondas de infraestructura:
   ```bash
   curl -fsS http://localhost/health/live
   curl -fsS http://localhost/health/ready
   ```
2. Ejecutar suite rápida de smoke tests:
   ```bash
   docker compose -f docker-compose.prod.yml exec -T backend pytest tests/test_healthcheck.py tests/test_phase46_health_readiness.py -q
   ```
3. Comprobar ausencia de excepciones en los logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs --tail=50 backend | grep -iE 'error|exception|fail'
   ```

---

## 4. Protocolo y Plantillas de Comunicación de Incidentes

La transparencia con la comunidad es un valor fundamental de **My Book Social**. Toda comunicación debe ser empática, precisa y libre de jerga técnica confusa.

### Canales de Difusión
1. **Banner In-App / Toast:** Publicado mediante endpoint `/api/v1/system/announcements/` para usuarios conectados.
2. **Página de Estado (Status Page):** Actualización pública del estado operacional.
3. **Canal de Soporte / Correo a Autores y Evaluadores:** Comunicación directa en incidencias que afecten publicaciones o monetización.

---

### Plantilla 1: Notificación Inicial de Incidencia (SEV-1 / SEV-2)

**Canal:** Banner en la aplicación y Página de Estado.  
**Tiempo límite de envío:** $< 10\text{ minutos}$ tras declarar el incidente.

> **Asunto / Título:** Estamos experimentando incidencias técnicas temporales  
> **Cuerpo:**  
> Hola a toda la comunidad de lectores y autores:  
> En este momento estamos detectando problemas técnicos que afectan al acceso y a la carga de algunas funciones de la plataforma (biblioteca y feed de lectura).  
> Nuestro equipo de ingeniería ya está interviniendo de manera activa para aislar el problema y restablecer el servicio a la normalidad en el menor tiempo posible.  
> Los datos de tu biblioteca, reseñas y lecturas se encuentran completamente a salvo.  
> Publicaremos una nueva actualización en cuanto tengamos novedades. Gracias por tu paciencia y apoyo.

---

### Plantilla 2: Actualización de Mitigación / Mantenimiento de Emergencia

**Canal:** Página de Estado y redes sociales oficiales.  
**Frecuencia:** Cada 30-45 minutos mientras el incidente permanezca activo.

> **Asunto / Título:** Actualización: Mantenimiento de emergencia en curso  
> **Cuerpo:**  
> Continuamos trabajando en la resolución de la incidencia técnica detectada.  
> Con el fin de salvaguardar la integridad de los datos y asegurar una recuperación limpia, hemos activado un breve período de mantenimiento controlado. Durante los próximos minutos el acceso a la plataforma puede estar restringido temporalmente.  
> Nuestro objetivo es restablecer la experiencia completa a la mayor brevedad. Seguiremos informando por esta vía.

---

### Plantilla 3: Notificación de Resolución y Servicio Restablecido

**Canal:** Banner In-App, Página de Estado y Notificación In-App.  
**Tiempo límite de envío:** Inmediatamente tras confirmar 10 minutos de métricas estables.

> **Asunto / Título:** Incidencia resuelta: My Book Social opera con total normalidad  
> **Cuerpo:**  
> Queremos comunicarte que la incidencia técnica que afectó temporalmente a la plataforma ha sido totalmente resuelta.  
> Todos los servicios —búsqueda, catálogo, club de lectura, reseñas y perfil social— se encuentran 100% operativos y estables. Todos tus datos y avances de lectura continúan intactos.  
> Agradecemos sinceramente tu comprensión y paciencia durante este proceso. Si experimentas cualquier comportamiento anómalo, por favor repórtalo directamente a través de nuestro botón de soporte y feedback.  
> ¡Feliz lectura!

---

### Plantilla 4: Resumen Post-Mortem y Transparencia Técnica

**Canal:** Blog de producto / Comunicación a la comunidad de autores.  
**Plazo de emisión:** 24 a 48 horas posteriores al incidente.

> **Asunto / Título:** Qué ocurrió y cómo lo hemos solucionado: Transparencia técnica en My Book Social  
> **Estructura obligatoria del comunicado:**  
> 1. **Resumen Ejecutivo:** Fecha, hora de inicio, hora de fin y duración total del impacto.  
> 2. **Qué sucedió:** Explicación comprensible del origen del fallo (ej. fallo de concurrencia en caché, degradación en migración).  
> 3. **Impacto en usuarios:** Funcionalidades afectadas y confirmación explícita de integridad de datos.  
> 4. **Medidas correctivas adoptadas:** Cambios arquitectónicos, nuevos tests automáticos y refuerzos de monitorización implementados para evitar su repetición.
