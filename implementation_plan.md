# Plan de Implementación: Listas Colaborativas (RoadmapV3 - Sección 30.2)

## 1. Contexto y Objetivos

Continuando con la **Sección 30 (Futuro / Funcionalidades avanzadas)** de [RoadmapV3.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV3.md), implementamos las **Listas Colaborativas**:
1. Permitir que una `ReadingList` sea marcada como colaborativa (`is_collaborative=True`).
2. Invitar a otros lectores a colaborar mediante `ReadingListCollaborator` con estados (`PENDING`, `ACCEPTED`, `REJECTED`) y permisos granulares (`can_add_books`, `can_remove_books`, rol `EDITOR`/`VIEWER`).
3. Trazabilidad: en cada `ReadingListItem`, registrar quién aportó el libro (`added_by`).
4. Autorización y permisos en `ReadingListViewSet`:
   - El dueño conserva el control total y puede invitar o remover colaboradores.
   - Los colaboradores aceptados con `can_add_books=True` pueden añadir libros y reordenar.
   - Los colaboradores pueden eliminar los libros que ellos mismos añadieron, o cualquier libro si disponen de `can_remove_books=True`.
   - El colaborador puede aceptar, rechazar o abandonar la colaboración.
5. Endpoints REST completos en `/api/v1/books/reading-lists/<id>/collaborators/`.
6. Experiencia frontend en `features/books/pages/ReadingLists.tsx`:
   - Pestaña / filtro "Listas Colaborativas".
   - Tarjetas con badge "Colaborativa" e indicador de colaboradores.
   - Modal de invitación y panel para aceptar/rechazar invitaciones.
   - Etiqueta "Añadido por @usuario" en los libros de la lista.

---

## 2. Cambios en Backend (Django / DRF)

### 2.1 Modelos (`backend/books/models.py`)
- **`ReadingList`**:
  - Añadir campo `is_collaborative = models.BooleanField(default=False, db_index=True)`.
- **`ReadingListItem`**:
  - Añadir campo `added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='added_reading_list_items')`.
- **`ReadingListCollaborator`**:
  - `reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name='collaborations')`
  - `user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='collaborative_lists')`
  - `role = models.CharField(max_length=20, choices=['EDITOR', 'VIEWER'], default='EDITOR')`
  - `status = models.CharField(max_length=20, choices=['PENDING', 'ACCEPTED', 'REJECTED'], default='PENDING', db_index=True)`
  - `can_add_books = models.BooleanField(default=True)`
  - `can_remove_books = models.BooleanField(default=False)`
  - `invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='sent_collaborations')`
  - Timestamps (`created_at`, `updated_at`).
  - Constraint `unique_together = ('reading_list', 'user')`.

### 2.2 Serializadores (`backend/books/serializers.py`)
- `ReadingListCollaboratorSerializer`: datos del usuario (`id`, `username`, `avatar_url`), `role`, `status`, `can_add_books`, `can_remove_books`, `invited_by`.
- Actualizar `ReadingListItemSerializer` para exponer `added_by` (`id`, `username`).
- Actualizar `ReadingListSerializer` y `ReadingListCreateUpdateSerializer` para exponer `is_collaborative`, `collaborators_count` y si el usuario actual es colaborador.

### 2.3 Vistas y Acciones (`backend/books/views.py`)
- En `ReadingListViewSet`:
  - `get_queryset`: soporte para `?collaborative=true`.
  - `add_book`: permitir si es el dueño o colaborador `ACCEPTED` con `can_add_books=True`. Registrar `added_by = request.user`.
  - `remove_book`: permitir si es dueño, si el colaborador tiene `can_remove_books=True` o si `item.added_by == request.user`.
  - Action `collaborators` (`GET`, `POST`): listar e invitar colaboradores.
  - Action `manage_collaborator` (`PATCH`, `DELETE`): aceptar invitación, actualizar permisos o revocar.

---

## 3. Cambios en Frontend (React 18 + TypeScript + Vite)

### 3.1 Tipos y API
- Extender tipos en `frontend/src/features/books/types/`: `ReadingListCollaborator`, flag `is_collaborative`, `added_by` en items.
- Servicios para `inviteCollaborator`, `acceptCollaboration`, `removeCollaborator`.

### 3.2 Interfaz (`ReadingLists.tsx`)
- Pestaña "Colaborativas".
- Badge en las listas colaborativas con avatares de colaboradores.
- Modal para invitar por nombre de usuario.
- Aceptación/rechazo de invitaciones pendientes.

---

## 4. Pruebas y Validación

1. **Backend Tests (`backend/tests/test_sprint10_collaborative_lists.py`)**:
   - `test_owner_can_invite_collaborator_and_set_permissions`
   - `test_collaborator_accept_invitation`
   - `test_collaborator_can_add_book_to_list`
   - `test_item_tracks_added_by_user`
   - `test_collaborator_cannot_remove_others_books_without_permission`
   - `test_collaborator_can_leave_list`
2. **Regresión Total Backend**:
   - Ejecutar la suite completa secuencial de Sprints 1 al 10 (71 tests).
3. **Frontend Validation**:
   - `npm run typecheck` (`tsc --noEmit`).
   - `npm run test` (Vitest).
   - `npm run build`.
4. **Documentación y Git**:
   - Actualizar `RoadmapV3.md`, `memory.md`, `CHANGELOG.md`.
   - Commit y push a `origin/develop`.
