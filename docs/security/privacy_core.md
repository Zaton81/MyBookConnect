# Arquitectura de Privacidad y Visibilidad — Privacy Core (Fase 2)

**MyBookConnect / My Book Social**  
**Fecha:** Septiembre de 2026  
**Módulo:** `backend/users/privacy_service.py` & `backend/users/policies.py`  
**Prioridad:** P0 — Bloqueante para Beta  

---

## 1. Visión General y Principio Fundamental

La plataforma adopta el principio de **Privacidad por Diseño (Privacy by Design)** y **Privacidad por Defecto (Privacy by Default)**:
- Ninguna superficie social asume que las restricciones de un perfil se aplican automáticamente a sus recursos derivados (feed, lecturas, afinidad, recomendaciones, listas).
- El nivel de privacidad del perfil (`privacy_level`) actúa como **techo máximo** para las opciones granulares de lectura (`reading_privacy_level`) y actividad (`activity_privacy_level`): un usuario con perfil privado tiene su biblioteca y actividad privadas por definición.
- La lógica de autorización y visibilidad no se dispersa en vistas ni serializadores: se centraliza en `PrivacyService` y se expone de forma canónica a través de `users.policies`.

---

## 2. Matriz de Privacidad y Visibilidad

| Recurso | Público | Solo Amigos / Seguidos | Privado | Regla de Bloqueo |
| :--- | :--- | :--- | :--- | :--- |
| **Perfil (`privacy_level`)** | Visible para todos | Visible solo para seguidores mutuos/seguidos | Visible solo para el propio usuario y administradores | Si A bloquea a B o B bloquea a A, denegado |
| **Biblioteca / Lecturas (`reading_privacy_level`)** | Visible para toda la comunidad | Visible solo para usuarios que sigo | Visible solo para el propio usuario | Excluido de búsquedas, listas y afinidad si hay bloqueo |
| **Actividad Social / Feed (`activity_privacy_level`)** | Aparece en el feed público | Aparece solo en el feed de seguidores | Nunca aparece en el feed social | Excluido tanto actor como target si hay bloqueo |
| **Mensajes Directos (`allow_messages_from`)** | Cualquier usuario registrado | Solo personas a las que sigo / amigos | Nadie puede enviar mensajes directos | Bloqueo bidireccional anula el envío |
| **Afinidad Literaria (`ReadingMatch`)** | Calculable si la lectura es pública | Calculable solo si el visor es amigo | Inaccesible (403 Forbidden) | Retorna 404 anti-enumeración ante bloqueo |
| **Lectores Similares (`SimilarReadersView`)** | Candidato K-NN elegible | Elegible solo si hay relación social | Excluido de candidatos K-NN | Usuarios mutuamente bloqueados excluidos |
| **Listas de Lectura (`ReadingList`)** | Visible para todos | Visible solo para seguidores | Solo visible para el creador | Creadores con perfil privado ocultan sus listas públicas a extraños |

---

## 3. Políticas Anti-Enumeración y Bloqueo Bidireccional

1. **Anti-Enumeración (HTTP 404):**
   - Cuando dos usuarios están bloqueados (`A bloquea a B` o `B bloquea a A`), intentar consultar la biblioteca específica (`/api/v1/books/user/books/?user_id=<id>`) o afinidad (`/api/v1/books/match/<id>/`) devuelve **HTTP 404 Not Found** en lugar de HTTP 403, impidiendo a atacantes o usuarios bloqueados inferir la existencia o actividad de la otra persona.
   - En el endpoint de perfil (`/api/v1/users/<id>/`), si el objetivo ha bloqueado al visor se devuelve `403 Forbidden` informando que no tiene acceso, mientras que el usuario bloqueador sí puede ver la cabecera mínima para gestionar el desbloqueo.

2. **Ruptura Inmediata de Seguimiento:**
   - La acción de bloqueo elimina bidireccionalmente e inmediatamente la relación de seguimiento (`following.remove`).

---

## 4. Redacción Dinámica de Campos en Serializadores (`UserSerializer`)

Al serializar un perfil de usuario para un tercero (no el propio usuario ni staff), `PrivacyService.apply_profile_field_visibility`:
1. **Elimina campos de configuración interna:** `reading_privacy_level`, `activity_privacy_level`, `allow_messages_from`, `show_email`, `show_birth_date`, `show_location`, `show_bio`.
2. **Redacta datos personales:**
   - `email`: Oculto a menos que `show_email=True` y el perfil sea público.
   - `birth_date`: Oculto a menos que `show_birth_date=True` y el perfil sea público.
   - `location` y `bio`: Redactados si sus banderas son falsas o el perfil no es público.
3. **Ofusca contadores sociales:** Si el visor no tiene permiso para ver lecturas o seguidores, los contadores retornan `0` y las listas retornan arrays vacíos.

---

## 5. Métodos de Filtrado a Nivel de Base de Datos (QuerySets)

Para evitar fugas en listados masivos y optimizar el rendimiento:
- `filter_visible_users(viewer, queryset)`: Excluye inactivos y usuarios con bloqueo bidireccional.
- `filter_visible_user_books(viewer, queryset)`: Filtra libros de usuarios considerando `privacy_level` y `reading_privacy_level`.
- `filter_visible_activities(viewer, queryset)`: Excluye eventos de usuarios bloqueados o privados en el feed.
- `filter_visible_reading_lists(viewer, queryset)`: Filtra listas según estado de la lista y privacidad del creador.
- `filter_visible_reviews(viewer, queryset)`: Excluye reseñas moderadas, autores privados o bloqueados.
