# Guía y Criterios de Salida de Beta Abierta — MyBookConnect

## 1. Visión y Alcance de la Beta Abierta
La **Beta Abierta** representa la apertura controlada de MyBookConnect a escala pública sin requerir código de invitación exclusivo. Durante esta fase, el foco se traslada a la estabilidad bajo tráfico real, la medición de retención de cohortes, el soporte formal a usuarios y el control de costes de infraestructura.

---

## 2. Matriz de Criterios de Salida de Beta Abierta (Secciones 33 y 45 del Roadmap)

| Requisito / Condición | Estado | Evidencia y Mecanismo Operativo |
| :--- | :--- | :--- |
| **P0 = 0 (Cero bloqueantes)** | ✅ Cumplido | Suite de regresión pasando al 100% en backend (>680 tests) y frontend (31 tests). |
| **Vulnerabilidades Críticas = 0** | ✅ Cumplido | Auditoría IDOR, rate limiting resiliente, JWT con rotación y blacklist en Redis. |
| **Privacidad Auditada** | ✅ Cumplido | `PrivacyService` centralizado, anti-enumeración 404 ante bloqueo mutuo, RGPD Art. 17 y 20. |
| **Backups Automatizados** | ✅ Cumplido | `backup_db.sh` y `backup_media.sh` diarios con cifrado AES-256 y retención de 30 días. |
| **Restore y Rollback Probado** | ✅ Cumplido | Procedimiento verificado mediante `test_restore_cycle.sh` con RTO < 15 min y RPO < 24h. |
| **CI/CD Estable** | ✅ Cumplido | GitHub Actions modulares (`ci-backend`, `ci-frontend`, `ci-docker`, `security`). |
| **Monitorización Activa** | ✅ Cumplido | Sondas desacopladas `/health/live` y `/health/ready`, logs JSON estructurados. |
| **Tasa de Error Conocida** | ✅ Cumplido | Presupuesto SLA API p95 < 500ms, tasa de respuestas 5xx esperada < 0.2%. |
| **Costes Operativos Conocidos** | ✅ Cumplido | Costes de computación acotados; cuotas e inferencia LLM con limitación de tokens. |
| **Retención Inicial Medida** | ✅ Cumplido | Métricas de cohortes D1, D7 y D30 integradas en `AnalyticsService.get_retention_metrics`. |
| **Soporte Formal al Usuario** | ✅ Cumplido | Módulo `SupportTicket` con creación, seguimiento y triaje administrativo. |
| **Moderación Activa** | ✅ Cumplido | Cola de reportes centralizada (`Report`), 5 limitadores de spam y `AuditLog`. |
| **Políticas Legales** | ✅ Cumplido | 7 documentos normativos sembrados y expuestos en `/legal/` y footer. |

---

## 3. Retención de Cohortes (D1, D7, D30)

El módulo de analítica (`analytics`) calcula la retención continua de usuarios registrados evaluando su actividad subsiguiente en hitos temporales estandarizados:

- **D1 (Día 1)**: Actividad registrada entre las 24h y 48h posteriores al registro (`signup`). Indica activación exitosa tras onboarding.
- **D7 (Día 7)**: Actividad entre los 6 y 8 días tras el registro. Indica formación de hábito lector y social.
- **D30 (Día 30)**: Actividad entre los 27 y 33 días tras el registro. Métrica fundamental de retención mensual (MAU).

### Consulta de Retención
- **Endpoint**: `GET /api/v1/analytics/retention/?days=30`
- **Permisos**: `IsAdminUser`
- **Respuesta**:
  ```json
  {
    "timeframe_days": 30,
    "total_signups": 150,
    "d1_active_users": 65,
    "d1_retention_rate": 0.4333,
    "d7_active_users": 38,
    "d7_retention_rate": 0.2533,
    "d30_active_users": 22,
    "d30_retention_rate": 0.1467
  }
  ```

---

## 4. Canal de Soporte de Usuario (`SupportTicket`)

Para canalizar consultas que trascienden el feedback técnico puntual (problemas de cuenta, dudas normativas, incidencias de catálogo), se habilita el módulo de soporte:

- **Categorías**:
  - `account`: Cuentas, contraseñas y accesos.
  - `technical`: Errores de navegación, visualización o fallos de red.
  - `content`: Sugerencias o correcciones de metadatos de libros y autores.
  - `other`: Otras consultas generales.
- **Estados**: `open` -> `in_progress` -> `resolved` -> `closed`.
- **Prioridades**: `low`, `medium`, `high`, `critical`.
- **Endpoints**:
  - `POST /api/v1/beta/support/`: Apertura de ticket por usuario autenticado.
  - `GET /api/v1/beta/support/my/`: Consulta de historial de tickets del propio usuario.
  - `GET /api/v1/beta/admin/support/`: Cola global para administradores con filtrado por categoría y estado.
  - `PATCH /api/v1/beta/admin/support/<id>/`: Respuesta administrativa (`admin_response`) y resolución.

---

## 5. Catálogo de Errores Conocidos y Mitigaciones

1. **Microcortes de Redis**:
   - *Riesgo*: Caída temporal de Redis afecta a caché y throttles.
   - *Mitigación implementada*: Wrappers `safe_cache_get/set` con degradación elegante a base de datos y `ResilientUserRateThrottle` que permite peticiones legítimas sin lanzar HTTP 500.
2. **Indisponibilidad del Proveedor de IA / LLM**:
   - *Riesgo*: Timeout o caída del API de OpenAI/Ollama.
   - *Mitigación implementada*: Fallback determinista local en `books/ai_views.py` entregando análisis contextualizados pre-generados sin interrumpir la experiencia de lectura.
3. **Bloqueo Transaccional en Entornos de Test**:
   - *Riesgo*: Ejecución simultánea de comandos `pytest` bloquea PostgreSQL (`test_booksocial`).
   - *Mitigación*: Regla de oro documentada en `memory.md` de ejecución estrictamente secuencial de suites de prueba.
