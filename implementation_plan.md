# Plan de Implementación: Administración, Moderación y Sistema de Reportes (RoadmapV3 - Secciones 24 y 25)

## 1. Contexto y Objetivos

Con los Sprints 1 a 6 concluidos y el hito de Preproducción alcanzado, abordamos las Secciones 24 y 25 de [RoadmapV3.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV3.md):
- **Sección 24 (Administración y Moderación)**:
  - **Usuarios**: Buscar, suspender, reactivar, ver actividad completa y consultar expedientes de reportes asociados.
  - **Libros**: Editar, fusionar duplicados administrativamente, corregir y ocultar.
  - **Autores**: Editar, fusionar duplicados administrativamente y ver historial de reclamaciones.
  - **Contenido**: Moderar reseñas, comentarios, mensajes, publicaciones sociales y listas.
- **Sección 25 (Sistema Universal de Reportes)**:
  - Extender el sistema para admitir reportes sobre `user`, `review`, `comment`, `message`, `list`, `book`, `author` y `post` (`UserPost`).
  - Estados normalizados (`pending/open`, `reviewing/under_review`, `resolved`, `rejected/dismissed`).
  - Registro auditable de usuario denunciante, fecha, motivo, moderador responsable, notas de resolución y timestamp.

---

## 2. Cambios en Backend

### 2.1 Ampliación de Modelos de Reporte y Serializadores
- **Archivo**: `backend/users/moderation_serializers.py`
  - Añadir `Book`, `Author`, `UserPost` a `ALLOWED_TARGET_MODELS`.
  - En `ReportListSerializer.get_target_type(obj)`: soportar `book`, `author`, `post`.
  - En `ReportListSerializer.get_target_preview(obj)`:
    - `Book`: vista previa con título, autor, ISBN, portada.
    - `Author`: vista previa con nombre, estado de verificación, biografía resumida.
    - `UserPost`: vista previa con autor, usuario destinatario y fragmento de texto.
  - En `ReportCreateSerializer.validate()`:
    - Prevenir auto-denuncias de publicaciones (`post.author == user`).
    - Validar existencia del objeto denunciado.

### 2.2 Sanciones Disciplinarias y Moderación de Contenido
- **Archivo**: `backend/users/moderation_views.py`
  - En `AdminReportDetailView.perform_update()`:
    - Para `HIDE_CONTENT`: soportar ocultar `UserPost` (eliminando o marcando moderado), `Review`, `ReviewComment`, `Message`, `ReadingList`.
    - Para `RESTORE_CONTENT`: restaurar visibilidad según corresponda.
    - Sanciones a usuarios (`BAN_USER`, `MUTE_USER_24H`, `MUTE_USER_7D`) con registro de auditoría (`AuditAction`).

### 2.3 Endpoints Administrativos de Catálogo y Usuarios
- **Archivo**: `backend/books/admin_views.py`
  - **`AdminBookMergeView`**: `POST /api/v1/admin/books/merge/`
    - Recibe `{ "canonical_id": int, "duplicate_ids": [int, ...] }`.
    - Llama a `merge_books(canonical, duplicates)` de forma atómica.
  - **`AdminAuthorMergeView`**: `POST /api/v1/admin/authors/merge/`
    - Recibe `{ "canonical_id": int, "duplicate_ids": [int, ...] }`.
    - Reasigna obras (`all_books` y `books`), unifica aliases y transfiere verificación de forma atómica.
  - **`AdminUserActivityView`**: `GET /api/v1/admin/users/<pk>/activity/`
    - Devuelve actividades cronológicas (`Activity`), posts en muro (`UserPost`) y reseñas.
  - **`AdminUserReportsView`**: `GET /api/v1/admin/users/<pk>/reports/`
    - Devuelve lista de reportes donde el usuario fue denunciante o denunciado.
- **Archivo**: `backend/books/admin_urls.py`
  - Registrar endpoints de fusión y de actividad/reportes de usuarios.

---

## 3. Cambios en Frontend (`AdminDashboard.tsx`)

- **Pestaña Usuarios (`users`)**:
  - Modal o panel para inspeccionar "Actividad del Usuario" y "Expedientes de Reportes".
  - Botones de acción directa: "Suspender Cuenta" y "Reactivar Cuenta".
- **Pestaña Catálogo (`catalog`)**:
  - Modal interactivo de fusión para libros y autores: selección de ficha duplicada para fusionar atómicamente con la canónica seleccionada.
- **Pestaña Denuncias (`reports`)**:
  - Filtro y visualización de denuncias sobre libros, autores y posts sociales con vista previa enriquecida.

---

## 4. Suite de Tests y Validación

1. **Backend Tests**:
   - Crear `backend/tests/test_sprint7_admin_and_moderation.py`:
     - Test de creación de reportes sobre libros, autores y posts.
     - Test de prevención de auto-denuncias y duplicados pendientes.
     - Test de resolución de reportes con acciones disciplinarias (`HIDE_CONTENT`, `BAN_USER`).
     - Test de endpoint `POST /api/v1/admin/books/merge/`.
     - Test de endpoint `POST /api/v1/admin/authors/merge/`.
     - Test de endpoints de actividad y reportes de usuario.
2. **Regresión Total**:
   - Ejecutar la suite completa secuencial de Sprints 1 a 7.
3. **Frontend Validation**:
   - `npm run typecheck` (`tsc --noEmit`) con 0 errores.
   - `npm run test` (Vitest) 100% pasando.
   - `npm run build` exitoso.
4. **Documentación y Git**:
   - Actualizar `RoadmapV3.md` (marcar completadas Secciones 24 y 25), `memory.md`, `CHANGELOG.md`.
   - Commit semántico y push a `origin/develop`.
