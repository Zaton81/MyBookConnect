# Manual de Guardia y Respuesta a Incidentes (On-Call Runbook) — My Book Social

**Versión:** 1.0.0 (General Availability)  
**Última actualización:** 14 de Octubre de 2026  
**Ámbito:** Operaciones de Producción y Guardias 24/7  
**Estado:** Activo y Obligatorio para el Equipo de Infraestructura y Backend  

---

## 1. Introducción y Filosofía Operativa

Este manual establece los procedimientos, niveles de servicio (SLA), matriz de escalado y flujos de trabajo que rigen la rotación del equipo de guardia (**On-Call Rotation**) de **My Book Social** tras el lanzamiento en **General Availability (GA)**.

Nuestra filosofía operativa se basa en:
1. **Prioridad al Usuario:** Restaurar la disponibilidad y funcionalidad de la plataforma antes de investigar las causas profundas.
2. **Cultura Sin Culpa (Blameless):** Los errores son oportunidades de aprendizaje sistémico; los incidentes se analizan con enfoque en resiliencia de procesos y código.
3. **Automatización y Trazabilidad:** Todo incidente genera un registro auditable, métricas de resolución y un informe post-mortem.

---

## 2. Clasificación de Severidad y Acuerdos de Nivel de Servicio (SLAs)

| Severidad | Criterio de Impacto | SLA de Respuesta (ACK) | SLA de Mitigación | Frecuencia de Comunicación |
| :--- | :--- | :---: | :---: | :---: |
| **SEV-1 (Crítica)** | Caída total de la plataforma, inaccesibilidad de la base de datos, brecha de seguridad activa, corrupción masiva de datos o indisponibilidad completa de `/health/live`. | **$\le 15$ minutos** | **$\le 1$ hora** | Cada 15 minutos en canal de estado |
| **SEV-2 (Mayor)** | Degradación grave de un componente nuclear: fallo general de recomendaciones por IA, saturación crítica de colas Celery ($> 5000$ tareas en cola), latencia sostenida p95 $> 1000\text{ ms}$, fallo de autenticación para un segmento de usuarios. | **$\le 30$ minutos** | **$\le 4$ horas** | Cada 60 minutos |
| **SEV-3 (Menor)** | Funcionalidad degradada sin bloqueo crítico: lentitud en portadas de libros de terceros, errores puntuales en visualización de insignias, alertas cosméticas en interfaz web. | **$\le 2$ horas** | **$\le 24$ horas** | Actualización diaria en ticket |

---

## 3. Roles Durante la Guardia

1. **Ingeniero Primario de Guardia (Primary On-Call):**
   - Primer respondedor ante alertas automáticas (Sentry, sondas de salud, umbrales de latencia).
   - Acusa recibo (ACK) de la alerta dentro del SLA establecido.
   - Realiza el triaje inicial y lidera la mitigación.

2. **Ingeniero Secundario de Guardia (Secondary On-Call / Backup):**
   - Respaldo inmediato si el primario no acusa recibo en los primeros 10 minutos para un SEV-1.
   - Asiste al primario en análisis de causa raíz y tareas de soporte operativo.

3. **Comandante de Incidente (Incident Commander - IC):**
   - Asignado automáticamente en incidentes SEV-1 (habitualmente el Tech Lead o Senior SRE).
   - Coordina esfuerzos, delega tareas de mitigación y toma la decisión final sobre rollbacks.

4. **Responsable de Comunicación (Communications Lead):**
   - Notifica a stakeholders internos y actualiza la página pública de estado de acuerdo con la [Guía de Comunicación y Rollback](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/rollback_and_incident_communication_guide.md).

---

## 4. Fuentes y Canales de Alerta

Las alertas se originan en los siguientes sistemas automáticos:
1. **Sentry:** Excepciones no capturadas, picos anómalos de errores 5xx en la API Django y errores no controlados en frontend React.
2. **Sondas de Salud HTTP:**
   - `/health/live`: Comprueba la vivacidad básica del proceso de aplicación.
   - `/health/ready`: Comprueba la conectividad con PostgreSQL (`booksocial-db`) y Redis (`booksocial-cache`).
3. **Métricas Estructuradas:** Endpoint protegido `/api/v1/observability/metrics/` para métricas de tiempo de ejecución y rendimiento.
4. **Celery Worker & Beat:** Fallos de tareas en segundo plano o estancamiento de workers (`booksocial-celery-worker`).

---

## 5. Procedimiento de Actuación Paso a Paso

### Paso 1: Recepción y Acuse de Recibo (ACK)
- Al sonar la alerta (PagerDuty / Opsgenie / Telegram / SMS), el ingeniero primario debe marcar la alerta como reconocida (ACK).
- Si la alerta no es reconocida en 10 minutos (SEV-1), se escala de forma automática al secundario.

### Paso 2: Triaje y Declaración de Severidad
- Evaluar el impacto real en los usuarios:
  - ¿Afecta a la totalidad de la plataforma o a un subsistema aislado?
  - ¿Hay riesgo de pérdida de datos o brecha de privacidad?
- Clasificar formalmente como SEV-1, SEV-2 o SEV-3.

### Paso 3: Mitigación Inmediata
Consulte los manuales específicos para acciones inmediatas:
- **Fallo de Base de Datos o Cache:** Consulte [Incident Runbooks](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/incident_runbooks.md).
- **Rollback de Despliegue:** Si el incidente fue desencadenado por una actualización de código reciente, ejecute el rollback inmediatamente siguiendo la [Guía de Rollback](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/rollback_and_incident_communication_guide.md).
- **Diagnóstico Rápido de Contenedores:**
  ```bash
  docker compose ps
  docker compose logs --tail=100 backend
  docker compose logs --tail=100 celery-worker
  docker compose logs --tail=100 db
  docker compose logs --tail=100 cache
  ```

### Paso 4: Restauración y Validación
- Verificar que las sondas `/health/live` y `/health/ready` respondan con código `200 OK`.
- Comprobar que la latencia nominal se haya estabilizado por debajo de los umbrales de alerta.

### Paso 5: Post-Mortem Blameless
- En un plazo máximo de **48 horas laborables** tras la resolución de un incidente SEV-1 o SEV-2, el Comandante de Incidente debe redactar el informe post-mortem.
- Estructura mínima requerida:
  1. Cronología exacta de los hechos (UTC).
  2. Causa raíz identificada (Técnica / Configuración / Procesos).
  3. Impacto en usuarios (duración del corte, solicitudes afectadas).
  4. Qué funcionó bien y qué falló en la respuesta.
  5. Elementos de acción preventivos con tickets asignados y fechas límite.

---

## 6. Documentos y Enlaces Relacionados

- [Manual de Operaciones y Mantenimiento](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/operations_runbook.md)
- [Guía de Respuesta a Incidentes y Runbooks Específicos](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/incident_runbooks.md)
- [Guía de Rollback y Comunicación de Incidentes](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/rollback_and_incident_communication_guide.md)
- [Guía de Despliegue y General Availability](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/deployment/general_availability_release_guide.md)
- [Informe de Cierre de Fase Beta](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/deployment/beta_closure_report.md)
