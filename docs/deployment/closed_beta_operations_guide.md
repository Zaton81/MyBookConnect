# Guía de Operaciones de Beta Cerrada y Monitorización — MyBookConnect

## 1. Introducción y Objetivos

La **Beta Cerrada** de **MyBookConnect** (`v1.0.0-rc1`) tiene como objetivo evaluar el comportamiento de la plataforma con evaluadores reales en condiciones controladas, midiendo la estabilidad operativa, la adopción y la calidad de la experiencia antes de abrir el registro público.

### Objetivos Clave:
- Validar flujos de onboarding, biblioteca, reseñas, mensajería y recomendaciones bajo tráfico real.
- Detectar anomalías y fricciones de usabilidad mediante el canal formal de feedback in-app.
- Mantener una observabilidad continua sobre la salud del sistema y responder a incidencias según SLAs definidos.

---

## 2. Gestión de Cohortes y Emisión de Invitaciones

### 2.1 Comando CLI de Generación de Cohortes

Para emitir un lote seguro de invitaciones para una cohorte de evaluadores:

```bash
# Ejemplo: Generar 30 invitaciones para la cohorte ALFA con 30 días de validez
python manage.py generate_beta_cohort --cohort ALFA --count 30 --max-uses 1 --days 30 --export-json /app/backups/alfa_cohort.json --export-csv /app/backups/alfa_cohort.csv
```

### 2.2 Parámetros del Comando

| Parámetro | Tipo | Descripción | Default |
| :--- | :--- | :--- | :--- |
| `--cohort` | `string` | Nombre o prefijo de la cohorte (ej. `ALFA`, `FOUNDERS`). Máximo 12 caracteres. | `ALFA` |
| `--count` | `int` | Número total de invitaciones únicas a generar. | `20` |
| `--max-uses` | `int` | Límite de canjes permitidos por código. | `1` |
| `--days` | `int` | Días de vigencia antes de la fecha de expiración automática. | `30` |
| `--export-json` | `path` | Ruta de archivo opcional para exportar el lote en JSON. | *Opcional* |
| `--export-csv` | `path` | Ruta de archivo opcional para exportar el lote en CSV. | *Opcional* |

### 2.3 Formato y Seguridad de los Códigos
- Cada código sigue el patrón `{COHORTE}-{HEX_CRIPTOGRÁFICO}` (ej. `ALFA-9C3E1F82B7D4`).
- Longitud garantizada $\le 32$ caracteres, con unicidad verificada en base de datos.
- Generado con el módulo criptográfico estándar `secrets`.

---

## 3. Monitorización Operativa y Telemetría

El equipo de administración y operaciones puede consultar la salud y telemetría de la beta en tiempo real mediante el endpoint administrativo:

```bash
# Consulta de métricas agregadas (requiere token JWT de superusuario / staff)
curl -H "Authorization: Bearer <TOKEN_ADMIN>" http://localhost:8000/api/v1/beta/admin/metrics/ | jq .
```

### 3.1 Estructura del Resumen de Métricas

```json
{
  "invitations": {
    "total": 50,
    "active": 35,
    "used": 15,
    "total_uses": 15,
    "activation_rate_pct": 30.0
  },
  "feedback": {
    "total": 12,
    "unresolved": 3,
    "by_category": {
      "bug": 2,
      "confusing_ux": 6,
      "performance": 4
    },
    "by_status": {
      "new": 2,
      "in_review": 1,
      "resolved": 9
    }
  },
  "support": {
    "total": 4,
    "critical_or_high_open": 0,
    "by_priority": {
      "medium": 3,
      "low": 1
    },
    "by_status": {
      "open": 1,
      "resolved": 3
    }
  },
  "evaluators": {
    "active_last_7_days": 14
  }
}
```

---

## 4. Sistema de Alertas y Triaje de Incidencias

### 4.1 Disparadores Automáticos de Alerta
El sistema activa una alerta inmediata cuando:
1. Un evaluador reporta feedback categorizado como **`BUG`**.
2. Un evaluador crea un ticket de soporte con prioridad **`CRITICAL`** o **`HIGH`**.

### 4.2 Endpoint de Triaje de Alertas Activas
Para obtener la lista consolidada de incidencias que requieren atención del equipo:

```bash
curl -H "Authorization: Bearer <TOKEN_ADMIN>" http://localhost:8000/api/v1/beta/admin/alerts/ | jq .
```

### 4.3 Matriz de Severidad y SLAs de Respuesta

| Severidad | Criterio | SLA de Primera Respuesta | SLA de Resolución |
| :--- | :--- | :--- | :--- |
| **P0 — Bloqueante** | Caída de servicio, fallo en login o corrupción de datos. | $< 1$ hora | $< 4$ horas |
| **P1 — Crítica** | Funcionalidad principal rota (ej. no se pueden guardar reseñas). | $< 4$ horas | $< 24$ horas |
| **P2 — Media** | Problema cosmético, UX confusa o lentitud no crítica. | $< 24$ horas | $< 72$ horas |
| **P3 — Menor** | Sugerencia de mejora o petición de nueva funcionalidad. | $< 48$ horas | Próximo Sprint |

---

## 5. Criterios de Promoción de Cohorte (Apertura Beta Abierta)

Para expandir la beta cerrada o avanzar hacia la beta abierta:
1. **Estabilidad:** Tasa de disponibilidad del sistema $\ge 99.5\%$ en los últimos 14 días.
2. **Cero P0/P1:** Cero incidencias críticas o bloqueantes pendientes de resolver.
3. **Adopción:** Tasa de activación de invitaciones $\ge 50\%$.
4. **Satisfacción:** Ratio de feedback positivo o resuelto $\ge 80\%$.
