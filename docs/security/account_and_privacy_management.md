# Gestión de Cuenta, Seguridad y Privacidad RGPD (Fase 17)

## 1. Resumen Ejecutivo
Este documento describe la arquitectura, endpoints y políticas de gestión de cuenta, seguridad de identidad y derechos de los interesados (RGPD Arts. 17 y 20) implementados en **MyBookConnect**.

El objetivo es garantizar la confidencialidad, integridad y disponibilidad de la información de los usuarios, brindando herramientas transparentes y directas para la autodeterminación de sus datos personales.

---

## 2. Marco Normativo de Privacidad y Consentimiento

### 2.1 Campos de Consentimiento en `User`
El modelo de datos extiende a `AbstractUser` con los siguientes campos de trazabilidad temporal:
- `deleted_at`: Marca de tiempo (`DateTimeField`) nullable que indica si y cuándo la cuenta fue anonimizada y eliminada.
- `terms_accepted_at`: Marca de tiempo que registra cuándo el usuario aceptó los Términos de Servicio vigentes.
- `privacy_accepted_at`: Marca de tiempo que registra cuándo el usuario otorgó su consentimiento a la Política de Privacidad RGPD.

---

## 3. Endpoints y Mecanismos de Seguridad

### 3.1 Cambio Seguro de Email
- **Endpoint:** `POST /api/v1/users/email/change/`
- **Autenticación requerida:** JWT Bearer Token activo.
- **Requisitos de seguridad:**
  - **Reautenticación obligatoria:** El payload debe incluir `current_password`.
  - **Validación de unicidad:** Se comprueba que el nuevo email no pertenezca a ningún usuario activo.
  - **Normalización:** El correo se convierte a minúsculas y se valida formalmente según los estándares de Django `EmailValidator`.
  - **Trazabilidad:** Se emite un registro `AuditAction.EMAIL_CHANGE` en `AuditLog` con las IPs y contexto de la solicitud (sin registrar contraseñas en texto claro).

### 3.2 Derecho al Olvido / Eliminación de Cuenta (RGPD Art. 17)
- **Endpoint:** `POST /api/v1/users/account/delete/`
- **Autenticación requerida:** JWT Bearer Token activo.
- **Confirmación de doble factor:**
  - El usuario debe proporcionar `password` (reautenticación).
  - El usuario debe enviar la cadena `confirmation`: `"ELIMINAR"` o `"DELETE"` para mitigar acciones involuntarias.
- **Protección de continuidad administrativa:**
  - Si el usuario es el único superusuario activo en la plataforma (`active_superusers <= 1`), la solicitud es rechazada con un código HTTP 400 impidiendo que el sistema quede sin administración.
- **Protocolo de Anonimización y Limpieza Atómica:**
  - `user.is_active = False`
  - `user.deleted_at = timezone.now()`
  - `user.email = f"deleted_{user.pk}_{uuid.uuid4().hex[:8]}@deleted.local"`
  - `user.username = f"deleted_user_{user.pk}"`
  - Limpieza de datos personales: `first_name`, `last_name`, `bio`, `avatar` (borrado físico/referencia vacía), `reading_goal_books` (0), `reading_goal_year` (None), `website` (""), `location` ("").
  - `user.set_unusable_password()`
  - **Desvinculación social:**
    - Se eliminan todas las relaciones de seguimiento (`Follow.objects.filter(follower=user)` y `Follow.objects.filter(following=user)`).
    - Se eliminan los bloqueos de usuarios (`UserBlock.objects.filter(blocker=user)` y `UserBlock.objects.filter(blocked=user)`).
  - **Listas de Lectura:**
    - Todas las listas creadas por el usuario se marcan como privadas (`is_public = False`) y moderadas (`is_moderated = True`) para no ser visibles públicamente ni recomendadas.
  - **Comentarios en Reseñas:**
    - Se aplica soft-delete sobre los comentarios del usuario (`ReviewComment.objects.filter(user=user).update(is_deleted=True, deleted_at=timezone.now())`).
  - **Notificaciones:**
    - Se eliminan las notificaciones dirigidas al usuario (`Notification.objects.filter(recipient=user).delete()`).
  - **Revocación de Sesiones:**
    - Los tokens de refresco pendientes (`OutstandingToken`) del usuario son enviados a la lista negra (`BlacklistedToken`), forzando la desconexión inmediata en todos los dispositivos.
  - **Auditoría:** Se genera un evento `AuditAction.USER_DELETE` documentando la anonimización.

### 3.3 Portabilidad de Datos Personales (RGPD Art. 20)
- **Endpoint:** `GET /api/v1/users/account/export/`
- **Autenticación requerida:** JWT Bearer Token activo.
- **Formato de entrega:** Archivo JSON estructurado y normalizado (`application/json; charset=utf-8`) con cabecera `Content-Disposition: attachment; filename="mybookconnect_data_export_<username>_<timestamp>.json"`.
- **Estructura del payload de exportación:**
  ```json
  {
    "export_metadata": {
      "generated_at": "2026-09-27T12:00:00Z",
      "format_version": "1.0",
      "platform": "MyBookConnect"
    },
    "account": {
      "id": 12,
      "username": "lector_dev",
      "email": "lector@example.com",
      "first_name": "Lector",
      "last_name": "Dev",
      "date_joined": "2026-01-15T10:00:00Z",
      "bio": "Amante de la ciencia ficción",
      "location": "Madrid",
      "website": "https://example.com",
      "terms_accepted_at": "2026-01-15T10:00:00Z",
      "privacy_accepted_at": "2026-01-15T10:00:00Z"
    },
    "reading_activity": {
      "goal_year": 2026,
      "goal_books": 25,
      "user_books": [...]
    },
    "reviews": [...],
    "review_comments": [...],
    "reading_lists": [...],
    "social": {
      "following": [...],
      "followers": [...]
    }
  }
  ```
- **Auditoría:** Se genera un evento `AuditAction.DATA_EXPORT` registrando la solicitud de exportación.

---

## 4. Frontend: Experiencia de Usuario en Ajustes de Cuenta

La pantalla `EditProfile.tsx` integra una interfaz por pestañas:
1. **👤 Perfil:** Modificación de datos públicos (nombre, apellidos, biografía, avatar, ubicación, web).
2. **🔒 Seguridad:**
   - Formulario de cambio de contraseña actual y nueva.
   - Formulario de cambio de correo electrónico con validación de contraseña.
3. **🛡️ Privacidad & RGPD:**
   - Panel de Portabilidad de Datos: Descarga en un clic del informe JSON completo.
   - Panel de Zona de Peligro: Información sobre el Art. 17 RGPD y modal destructivo con reautenticación y texto de confirmación para eliminar la cuenta.
