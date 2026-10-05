# Plan de Implementación: Clubs de Lectura y Lecturas Conjuntas (RoadmapV3 - Sección 30.1)

## 1. Contexto y Objetivos

Con las fases 1 a 27 y preproducción completadas en `RoadmapV3.md`, iniciamos el bloque de funcionalidades avanzadas post-lanzamiento de la **Sección 30**, priorizando los **Clubs de Lectura y Lecturas Conjuntas (Book Clubs & Buddy Reads)**:

1. **Gestión de Clubs**: Creación de clubs de lectura con opciones de visibilidad (públicos y privados), descripción, reglas, portada y administración de miembros.
2. **Membresías y Roles**: Roles de usuario dentro del club (`ADMIN`, `MODERATOR`, `MEMBER`) y estados (`ACTIVE`, `PENDING_APPROVAL`, `BANNED`), permitiendo solicitudes de unión en clubs privados y auto-ingreso en públicos.
3. **Plan de Lecturas Conjuntas**: Libro en curso (`current_book`), lecturas programadas (`UPCOMING`) y lecturas finalizadas (`FINISHED`) con fechas estimadas y metas de capítulos.
4. **Hilos de Debate y Spoilers**: Discusiones temáticas por libro o generales, hilos fijados (`is_pinned`), soporte de advertencia de spoilers (`has_spoilers`) y comentarios anidados.
5. **Experiencia Frontend Premium**: Explorador de clubs, vista detallada con pestañas fluidas, interfaz accesible WCAG, diseño moderno acorde al sistema de diseño existente (Tailwind/CSS tokens).

---

## 2. Arquitectura de Datos y Backend (Django / DRF)

### 2.1 Modelos (`backend/books/models.py`)
- **`ReadingClub`**:
  - `name`: CharField(max_length=200)
  - `slug`: SlugField(unique=True, blank=True)
  - `description`: TextField(blank=True)
  - `cover_image`: ImageField(upload_to='club_covers/', null=True, blank=True)
  - `creator`: ForeignKey(User, related_name='created_clubs')
  - `is_private`: BooleanField(default=False)
  - `rules`: TextField(blank=True)
  - `current_book`: ForeignKey(Book, null=True, blank=True, on_delete=SET_NULL, related_name='active_in_clubs')
  - Timestamps (`created_at`, `updated_at`)
- **`ReadingClubMember`**:
  - `club`: ForeignKey(ReadingClub, related_name='memberships', on_delete=CASCADE)
  - `user`: ForeignKey(User, related_name='club_memberships', on_delete=CASCADE)
  - `role`: TextChoices (`ADMIN`, `MODERATOR`, `MEMBER`)
  - `status`: TextChoices (`ACTIVE`, `PENDING_APPROVAL`, `BANNED`)
  - `joined_at`: DateTimeField(auto_now_add=True)
  - `unique_together = ('club', 'user')`
- **`ReadingClubBook`**:
  - `club`: ForeignKey(ReadingClub, related_name='reading_plan', on_delete=CASCADE)
  - `book`: ForeignKey(Book, related_name='club_readings', on_delete=CASCADE)
  - `status`: TextChoices (`CURRENT`, `UPCOMING`, `FINISHED`)
  - `start_date`, `end_date`: DateField(null=True, blank=True)
  - `target_milestones`: CharField(max_length=255, blank=True)
  - `created_at`: DateTimeField(auto_now_add=True)
- **`ReadingClubDiscussion`**:
  - `club`: ForeignKey(ReadingClub, related_name='discussions', on_delete=CASCADE)
  - `book`: ForeignKey(Book, null=True, blank=True, on_delete=SET_NULL, related_name='club_discussions')
  - `title`: CharField(max_length=255)
  - `content`: TextField()
  - `author`: ForeignKey(User, related_name='club_discussions', on_delete=CASCADE)
  - `is_pinned`: BooleanField(default=False)
  - `has_spoilers`: BooleanField(default=False)
  - Timestamps (`created_at`, `updated_at`)
- **`ReadingClubDiscussionComment`**:
  - `discussion`: ForeignKey(ReadingClubDiscussion, related_name='comments', on_delete=CASCADE)
  - `author`: ForeignKey(User, related_name='club_discussion_comments', on_delete=CASCADE)
  - `content`: TextField()
  - `has_spoilers`: BooleanField(default=False)
  - Timestamps (`created_at`, `updated_at`)

### 2.2 Serializadores (`backend/books/club_serializers.py`)
- Serializadores detallados y ligeros para listados, detalle, miembros, plan de lectura y debates con conteo de comentarios.
- Sanitización anti-XSS en descripciones, reglas y comentarios de debate.

### 2.3 Vistas y Rutas (`backend/books/club_views.py` & `backend/books/club_urls.py`)
- `GET /api/v1/clubs/`: Explorar clubs públicos y filtrar por pertenencia (`my_clubs=true`) o término de búsqueda (`q`).
- `POST /api/v1/clubs/`: Crear club (creador adquiere rol `ADMIN` automático).
- `GET /api/v1/clubs/<slug>/`: Consulta detallada del club y estado de membresía del usuario actual.
- `PATCH /api/v1/clubs/<slug>/`: Modificación (exclusivo para `ADMIN`).
- `POST /api/v1/clubs/<slug>/join/`: Unirse al club (`ACTIVE` si es público, `PENDING_APPROVAL` si es privado).
- `POST /api/v1/clubs/<slug>/leave/`: Salir del club.
- `GET /api/v1/clubs/<slug>/members/`: Lista de miembros y roles.
- `PATCH /api/v1/clubs/<slug>/members/<user_id>/`: Moderar miembro / aprobar ingreso (solo `ADMIN`/`MODERATOR`).
- `POST /api/v1/clubs/<slug>/books/`: Añadir lectura al plan o actualizar libro actual.
- `GET/POST /api/v1/clubs/<slug>/discussions/`: Hilos de debate del club.
- `GET /api/v1/clubs/<slug>/discussions/<pk>/`: Detalle del debate y comentarios.
- `POST /api/v1/clubs/<slug>/discussions/<pk>/comments/`: Comentar en un debate.

---

## 3. Frontend (React 18 + TypeScript + Vite)

### 3.1 Tipos y Servicios (`frontend/src/features/clubs/`)
- `types/index.ts`: Definición de interfaces `ReadingClub`, `ReadingClubMember`, `ReadingClubBook`, `ReadingClubDiscussion`, `ReadingClubComment`.
- `services/clubService.ts`: Clientes de API con Axios para todos los endpoints de clubs.

### 3.2 Páginas y Componentes
- `pages/ClubsPage.tsx`:
  - Listado de clubs con pestañas "Explorar Clubs" y "Mis Clubs".
  - Barra de búsqueda y filtros.
  - Botón y modal accesible para "Crear Club".
- `pages/ClubDetailPage.tsx`:
  - Banner, información general, badges de privacidad (`Público` / `Privado`).
  - Botones contextuales: `Unirse`, `Solicitar acceso`, `Salir`, `Gestionar`.
  - Pestañas organizadas:
    - **Lecturas**: Libro actual con enlace a detalle de libro, barra de avance, historial de lecturas conjuntas y botón para proponer/añadir nuevo libro (para admins/moderadores).
    - **Debates**: Foro del club, temas fijados, indicador de spoilers con blur/reveal y modal para nuevo tema.
    - **Miembros**: Listado de integrantes, roles destacados y panel de aprobación de solicitudes si es admin.
- Integración en navegación: enlace en `Navbar.tsx` y rutas `/clubs` y `/clubs/:slug` en `App.tsx`.

---

## 4. Pruebas y Validación

1. **Backend Tests (`backend/tests/test_sprint9_reading_clubs.py`)**:
   - `test_create_club_and_auto_admin_membership`
   - `test_join_public_club_and_request_private_club`
   - `test_admin_can_approve_member_and_change_roles`
   - `test_club_reading_plan_and_current_book`
   - `test_club_discussions_with_spoilers_and_permissions`
2. **Regresión Total Backend**:
   - Ejecución secuencial de los tests (Sprints 1 al 9) garantizando 100% de éxito.
3. **Frontend Tests & Build**:
   - Test unitario de `ClubsPage.test.tsx` en Vitest.
   - `npm run typecheck` (`tsc --noEmit`) con 0 errores.
   - `npm run test` (Vitest) 100% pasando.
   - `npm run build` exitoso.
4. **Documentación y Git**:
   - Actualizar `RoadmapV3.md`, `memory.md`, `CHANGELOG.md`.
   - Commit y push a `origin/develop`.
