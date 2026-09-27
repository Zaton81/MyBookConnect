# Sistema de Notificaciones y Preferencias de Alertas — MyBookConnect

## 1. Visión General (Fase 23)

El sistema de notificaciones de **MyBookConnect** proporciona un canal unificado y en tiempo real para informar a los usuarios sobre interacciones sociales relevantes, actividades de lectura y descubrimientos en la plataforma, respetando siempre las preferencias individuales de cada usuario y las políticas de privacidad y seguridad.

---

## 2. Eventos y Tipos de Notificación

El modelo `NotificationType` en el backend categoriza las siguientes interacciones:

| Tipo | Etiqueta | Disparador | Canal In-App por Defecto | Canal Email por Defecto |
| :--- | :--- | :--- | :--- | :--- |
| `FOLLOW` | Nuevo seguidor | Un usuario comienza a seguir a otro | Activo (`True`) | Opcional (`False`) |
| `FOLLOW_ACCEPTED` | Solicitud aceptada | Se aprueba solicitud de seguimiento en perfiles privados | Activo (`True`) | Opcional (`False`) |
| `LIKE` | Me gusta en reseña | Un lector marca como útil/like una reseña | Activo (`True`) | Opcional (`False`) |
| `COMMENT` | Comentario | Comentario en una reseña o lista de lectura | Activo (`True`) | Activo (`True`) |
| `REPLY` | Respuesta | Respuesta directa a un comentario previo | Activo (`True`) | Activo (`True`) |
| `LIST_FOLLOW` | Lista social | Un lector guarda, clona o sigue una lista de lectura | Activo (`True`) | Opcional (`False`) |
| `MESSAGE` | Mensaje directo | Nuevo mensaje en una conversación privada de chat | Activo (`True`) | Activo (`True`) |
| `RECOMMENDATION` | Recomendación | Nueva sugerencia de libro por afinidad o compartición | Activo (`True`) | Activo (`True`) |
| `SYSTEM` | Sistema | Comunicados oficiales, moderación o seguridad | Activo (`True`) | Opcional |

---

## 3. Modelo de Preferencias Granulares (`NotificationPreference`)

Cada cuenta de usuario posee un registro `NotificationPreference` asociado de manera 1:1, accesible y modificable a través de la API:
- **Endpoints:**
  - `GET /api/v1/users/notifications/preferences/`: recupera el estado de configuración de todos los canales.
  - `PATCH /api/v1/users/notifications/preferences/`: actualización parcial de switches (`in_app_*`, `email_*`, `push_enabled`).
- **Canales contemplados:**
  - **In-App:** Notificación persistente en base de datos visible en el Header y en el Centro de Notificaciones.
  - **Email:** Envío transaccional seguro y asíncrono hacia el correo verificado del usuario.
  - **Push:** Flag preparado para Web Push / notificaciones PWA futuras.

---

## 4. Servicio Centralizado `NotificationService`

Toda emisión de alertas se canaliza a través de `NotificationService.send_notification(...)`:

```python
NotificationService.send_notification(
    recipient=user_to_notify,
    actor=current_user,
    notif_type=NotificationType.COMMENT,
    title='Nuevo comentario',
    message='...',
    link='/books/42',
)
```

### Reglas de Negocio y Privacidad Inviolables:
1. **No Auto-Notificación:** Si `actor == recipient`, la alerta se descarta silenciosamente.
2. **Bloqueos Sociales Bidireccionales:** Si existe un bloqueo activo entre `actor` y `recipient` (`PrivacyService.are_mutually_blocked`), nunca se genera la notificación ni se notifica al bloqueador/bloqueado.
3. **Usuarios Silenciados:** Si el destinatario ha silenciado al actor (`recipient.muted_users`), las alertas del actor no se generan.
4. **Respeto a Preferencias:** Si el usuario desactivó el canal `in_app` o `email` para ese tipo específico de evento, el servicio no creará el registro ni enviará el correo.

---

## 5. Endpoints de Notificaciones

- `GET /api/v1/users/notifications/`: listado paginado con filtros (`?unread=1`, `?type=...`).
- `GET /api/v1/users/notifications/unread-count/`: conteo rápido para badge en la cabecera.
- `POST /api/v1/users/notifications/<id>/read/`: marca una notificación individual como leída.
- `POST /api/v1/users/notifications/read-all/`: marca todas las notificaciones pendientes como leídas.
- `DELETE /api/v1/users/notifications/<id>/`: elimina una notificación del historial.
- `POST /api/v1/users/notifications/clear-read/`: depuración en bloque de notificaciones leídas.

---

## 6. Interfaz de Usuario y Experiencia en Frontend

1. **Badge y Dropdown Dinámico (`Header.tsx`):**
   - Iconografía diferenciada por tipo (`👤`, `❤️`, `💬`, `↩️`, `📚`, `✨`, `✉️`, `📢`).
   - Acceso inmediato a "Marcar todas leídas" y enlace directo al centro completo.
2. **Centro de Notificaciones (`/notifications`):**
   - Pestañas de filtrado: Todas, No leídas, Interacciones y Reseñas, Seguidores y Listas.
   - Navegación al recurso origen al hacer clic.
   - Acciones individuales y limpieza masiva.
3. **Panel de Preferencias en Perfil (`/profile/edit` pestaña Notificaciones):**
   - Switches individuales para canales "En la app" y "Email" por cada categoría de interacción.
   - Guardado reactivo con feedback visual.
