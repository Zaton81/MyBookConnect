# Guía de Operaciones de Beta Pública y Campaña de Adopción — MyBookConnect

## 1. Introducción y Objetivos

La **Fase 37** establece la transición desde la cohorte restringida hacia la **Beta Pública y Adopción Controlada** de **MyBookConnect** (`v1.0.0-rc1`). Permite regular el ritmo de crecimiento orgánico mediante feature flags de backend, fomentar la viralidad mediante un sistema de referidos entre lectores y monitorizar de manera continua las métricas de retención de cohortes D1 / D7 / D30.

### Objetivos Principales:
1. **Acceso Flexible:** Permitir alternar en caliente entre registro abierto (`public`), registro restringido por invitación (`closed_beta`) o modo mantenimiento (`maintenance`) sin requerir despliegues de base de datos.
2. **Crecimiento Orgánico Viral:** Dotar a cada lector autenticado de un código de referido único para invitar a amigos, con seguimiento transparente de canjes y usos restantes.
3. **Monitorización de Retención:** Evaluar la persistencia de hábitos de lectura a los 1, 7 y 30 días posteriores al registro para garantizar tracción de producto antes del lanzamiento general.

---

## 2. Control Dinámico de Registro y Modos de Operación

El comportamiento del flujo de registro en `/api/v1/users/register/` está gobernado por dos variables de entorno en `settings.py`:

```python
PUBLIC_REGISTRATION_ENABLED = os.getenv('PUBLIC_REGISTRATION_ENABLED', 'true').lower() in ('true', '1', 'yes')
REQUIRE_BETA_INVITATION = os.getenv('REQUIRE_BETA_INVITATION', 'false').lower() in ('true', '1', 'yes')
```

### 2.1 Matriz de Modos de Registro

| `PUBLIC_REGISTRATION_ENABLED` | `REQUIRE_BETA_INVITATION` | Modo Reportado | Comportamiento en `/api/v1/users/register/` |
| :---: | :---: | :---: | :--- |
| `true` | `false` | `public` (Default) | Registro abierto universal. El campo `invitation_code` es opcional (se procesa si se provee). |
| `true` o `false` | `true` | `closed_beta` | Registro restringido. Se exige obligatoriamente un código de invitación/referido válido y activo. |
| `false` | `false` | `maintenance` | Registro deshabilitado por completo (útil en mantenimientos críticos o migraciones de infraestructura). |

### 2.2 Endpoint Público de Consulta de Estado

Las aplicaciones cliente (web SPA, mobile) pueden consultar el modo antes de renderizar los formularios de login o registro:

```http
GET /api/v1/beta/registration-status/
Content-Type: application/json
```

**Respuesta Exitosa (HTTP 200):**
```json
{
  "public_registration_enabled": true,
  "require_invitation": false,
  "mode": "public"
}
```

---

## 3. Programa Viral de Referidos entre Lectores

Cada lector registrado dispone de un canal de recomendación para compartir la plataforma con su comunidad literaria.

### 3.1 Obtención del Código Personal

```http
GET /api/v1/beta/referrals/my-code/
Authorization: Bearer <TOKEN_USUARIO>
```

**Respuesta (HTTP 200):**
```json
{
  "code": "REF-ALICE-4E9A12BC",
  "referral_url": "/register?ref=REF-ALICE-4E9A12BC",
  "max_uses": 50,
  "uses_count": 3,
  "remaining_uses": 47,
  "is_active": true
}
```

### 3.2 Cuadro de Estadísticas del Referidor

```http
GET /api/v1/beta/referrals/stats/
Authorization: Bearer <TOKEN_USUARIO>
```

**Respuesta (HTTP 200):**
```json
{
  "code": "REF-ALICE-4E9A12BC",
  "referral_url": "/register?ref=REF-ALICE-4E9A12BC",
  "uses_count": 3,
  "max_uses": 50,
  "remaining_uses": 47,
  "is_active": true,
  "created_at": "2026-10-01T15:30:00Z"
}
```

### 3.3 Ciclo de Vida del Código de Referido
- **Generación On-Demand:** Se genera automáticamente con formato `REF-{USERNAME}-{HASH}` (longitud $\le 32$ caracteres).
- **Consumo Atómico:** Cada nuevo registro que incluye el código en su carga útil descuenta un uso y desactiva la invitación al alcanzar `max_uses`.
- **Idempotencia:** Múltiples consultas devuelven la misma clave activa para el usuario.

---

## 4. Telemetría de Retención de Cohortes (D1 / D7 / D30)

El endpoint administrativo `/api/v1/beta/admin/metrics/` consolida la telemetría de producto e incluye la sección `retention`:

```bash
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/v1/beta/admin/metrics/ | jq .retention
```

**Muestra de Respuesta:**
```json
{
  "timeframe_days": 30,
  "total_signups": 142,
  "d1_active_users": 89,
  "d1_retention_rate": 0.6268,
  "d7_active_users": 64,
  "d7_retention_rate": 0.4507,
  "d30_active_users": 38,
  "d30_retention_rate": 0.2676
}
```

### 4.1 Definición de Ventanas de Retención
- **D1 (Día 1):** Actividad registrada entre 24h y 48h posteriores a la creación de la cuenta.
- **D7 (Día 7):** Actividad registrada entre el día 6 y el día 8 post-registro.
- **D30 (Día 30):** Actividad registrada entre el día 27 y el día 33 post-registro.

---

## 5. Procedimientos Operativos y Contingencia

### 5.1 Restringir el Acceso Inmediatamente (Contención de Incidencias)
Si se identifica una sobrecarga imprevista en base de datos o abuso de registros:
```bash
# Cambiar en el entorno de producción/staging
export REQUIRE_BETA_INVITATION="true"
docker compose restart backend
```
El endpoint `/api/v1/beta/registration-status/` cambiará instantáneamente a `"mode": "closed_beta"` y el formulario exigirá código válido.

### 5.2 Habilitar Modo Mantenimiento
Para detener nuevos registros durante ventanas de migración:
```bash
export PUBLIC_REGISTRATION_ENABLED="false"
export REQUIRE_BETA_INVITATION="false"
docker compose restart backend
```
El endpoint responderá `"mode": "maintenance"` y bloqueará todo alta con mensaje descriptivo.
