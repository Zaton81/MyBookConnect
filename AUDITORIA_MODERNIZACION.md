# Informe de auditoría y plan de modernización — MyBookConnect

**Fecha:** 8 de septiembre de 2026  
**Alcance:** backend Django/DRF, frontend React/Vite, Docker, integraciones de catálogo/IA y UX social  
**Estado del código:** **bloqueado para arrancar de forma fiable** por conflictos de merge sin resolver (`<<<<<<< Updated upstream`) en al menos 13 archivos.

Este documento es el artefacto de la Fase 0. **No se ha modificado código de producto.** Tras tu aprobación, se aplicará por pasos.

---

## Resumen ejecutivo

MyBookConnect es una red social de lectura (JWT, biblioteca personal, importación desde Google Books / Open Library / Wikipedia, chat con Channels, erratas, follow). El stack está **congelado en 2023–2024** y Django 5.0 **ya no tiene soporte**. Hay un **stash/merge a medias** que mezcla dos líneas de trabajo (recomendaciones + bloqueo de usuarios vs erratas + chat + amigos).

| Área | Salud | Comentario |
| --- | --- | --- |
| Integridad del repo | Crítica | Conflictos de merge; el proyecto no es compilable/ejecutable de forma predecible |
| Seguridad / dependencias | Alta | Django 5.0 EOL; Pillow 10.0.1 con CVE; `python-jose` vulnerable y no usado; JWT en `localStorage`; WebSocket sin JWT |
| Arquitectura backend | Media | Apps duplicadas (`backend/app`, `backend/config`); I/O HTTP síncrono en vistas; signals frágiles |
| Frontend | Media | Home vacío; cliente HTTP inconsistente; Quill 1 / Flowbite antiguos; tipos de React Router 5 |
| Docker / prod | Alta | Compose de prod incompleto; sin healthchecks ni usuario no-root; media en git |
| IA / social | Baja madurez | “IA” = scraping de APIs públicas; Home es placeholder; chat existe en API, poco en UX |

**Recomendación de destino (versiones estables a septiembre 2026):**

- Python **3.13** (Django 6.1 exige ≥ 3.12; la imagen actual es 3.11).
- Django **6.1.1** + DRF **3.18.0** (alternativa conservadora: Django **5.2 LTS**, soporte extendido hasta abril 2028).
- React **19.2.x** + Vite **8.2.x** + React Router **7**.
- PostgreSQL **16** o **17**, Redis **7.4**, Nginx **1.27**.

---

## Bloqueador previo (obligatorio antes de cualquier upgrade)

Marcadores de conflicto en:

- `backend/books/models.py`, `serializers.py`, `views.py`, `urls.py`, `services.py`
- `backend/users/models.py`, `serializers.py`, `views.py`, `urls.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/BookDetail.tsx`, `Profile.tsx`, `Author.tsx`, `Library.tsx`

Hay **dos ramas de producto que hay que unir, no elegir una sola**:

| Línea A (upstream) | Línea B (stash) |
| --- | --- |
| `blocked_users`, follow/block | `is_editor` |
| Recomendaciones por categoría | Erratas (modelo + API) |
| Refresh de libros por autor | Chat (`messages_app` + Channels) |
| Ruta `/profile/:id` | Rutas `/users/:userId` y `/friends` |

**Paso 0 acordado:** resolver conflictos conservando **ambas** capacidades, unificar rutas (`/users/:id` + alias `/profile`) y generar una sola migración coherente. Hasta entonces no tiene sentido actualizar paquetes.

---

## Fase 1 — Auditoría de dependencias

### 1.1 Backend (`backend/requirements.txt`)

| Paquete actual | Estado | Destino propuesto | Notas |
| --- | --- | --- | --- |
| `Django==5.0` | **EOL** (soporte extendido terminó ~abril 2025) | `Django==6.1.1` | DRF 3.18 **no soporta** Django 5.0/5.1. Subir Python a 3.12+. |
| `djangorestframework==3.14.0` | Obsoleto | `3.18.0` | Requiere Django 5.2 / 6.0 / 6.1 |
| `djangorestframework-simplejwt==5.3.1` | Atrasado | última 5.5.x compatible con DRF 3.18 | Falta `SIMPLE_JWT` en `mybookconnect/settings.py` (sí existe en el settings **legado** `backend/config/settings.py`) |
| `django-cors-headers==4.3.0` | Atrasado | 4.7+ | Colocar CORS **antes** de Common, como ya está |
| `psycopg2-binary==2.9.9` | Aceptable | `psycopg[binary]` 3.2.x | Driver moderno; `psycopg2` sigue vivo pero no es el camino a largo plazo |
| `Pillow==10.0.1` | **Vulnerable** | `Pillow==12.2.0` o `12.3.0` | CVE-2024-28219, CVE-2026-42308/42310 y posteriores; 10.0.1 es de sept. 2023 |
| `python-jose[cryptography]==3.3.0` | **Vulnerable y no usado** | **Eliminar** | CVE-2024-29370 (DoS JWE). SimpleJWT no lo necesita |
| `python-dotenv==1.0.0` | Atrasado | 1.1.x | En Docker es redundante si se usa `env_file` |
| `django-storages==1.14.2` | Atrasado / no cableado | 1.14.6+ **o quitar** hasta usar S3/R2 | Media local hoy |
| `gunicorn==21.2.0` | Atrasado y **no usado** | Quitar **o** usarlo con Uvicorn workers | El contenedor corre **Daphne** |
| `requests==2.32.3` | OK / sustituible | `httpx` 0.28+ | Mejor para timeouts, HTTP/2 y async |
| `channels`, `channels-redis`, `daphne` | **Sin pin** | Pin de majors compatibles con Django 6.1 | Builds no reproducibles |
| — | Ausente | `django-filter`, `drf-spectacular` | Filtros y OpenAPI |
| — | Ausente | `whitenoise` | Estáticos en prod sin Nginx extra en el API |

**Python:** Dockerfile `python:3.11-slim`. Django 6.1 documenta 3.12 / 3.13 / 3.14 → **Python 3.13-slim**.

### 1.2 Frontend (`frontend/package.json`)

| Paquete actual | Estado | Destino propuesto | Notas |
| --- | --- | --- | --- |
| `react` / `react-dom` 18.3.1 | Una major atrás | **19.2.7** (u último 19.2.x) | Compiler opcional después |
| `vite` ^5.2.0 | Dos majors atrás | **8.2.x** | Node 20.19+ / 22.12+; Rolldown |
| `@vitejs/plugin-react` ^4.3.1 | Atrasado | v6 (pareja de Vite 8) | |
| `react-router-dom` 6.22.0 | Atrasado | **7.x** | Tipos `@types/react-router-dom` **5.3.3** son incorrectos para v6/v7; en v7 los tipos van en el propio paquete |
| `typescript` ^5.4.5 | Atrasado | 5.9.x | |
| `tailwindcss` ^3.4.4 | Estable | 3.4 último **o** Tailwind 4 en un paso aparte | v4 es migración de config, no mezclar con React 19 el mismo día |
| `flowbite` 2.3 / `flowbite-react` 0.7 | Muy atrasado | Último flowbite-react **o migrar a** componentes propios / Headless UI | Riesgo de churn |
| `react-quill` 2.0.0 + `quill` 1.3.7 | **Abandonado / inseguro** | **TipTap** o `react-quill-new` + Quill 2 | Quill 1 tiene historial XSS; ya usáis DOMPurify (bien) |
| `axios` ^1.7.2 | **No se usa** | Quitar | El código usa `fetch` |
| `zustand` ^5.0.8 | Actual | Mantener 5.x | Buen hallazgo |
| `dompurify` ^3.0.6 | Atrasado | 3.2.x | Seguir sanitizando HTML de bios |
| pnpm 8.15.4 (Dockerfile) | Atrasado | pnpm 10.x | Alinear lockfile |

**Ausentes recomendados:** TanStack Query v5 (caché/servidor), cliente HTTP único (`ky` o wrapper `fetch`), Vitest + Testing Library, ESLint 9 + typescript-eslint.

### 1.3 Plan de actualización (orden, no simultáneo)

1. **Paso 0 — Conflictos.** Unificar modelos/rutas/UI. El proyecto debe arrancar.
2. **Paso 1 — Higiene.** Quitar `python-jose`, `axios` no usado, `gunicorn` o usarlo de verdad. Pin de Channels/Daphne/Redis. `.gitignore` para `backend/media/` (hoy hay portadas commiteadas).
3. **Paso 2 — Python 3.13 + Django 5.2.x LTS** (aterrizaje) y tests de humo API. Luego, si se aprueba, **Django 6.1.1 + DRF 3.18**.
4. **Paso 3 — Pillow 12.x, psycopg3, simplejwt, cors-headers.**
5. **Paso 4 — Frontend: Vite 8 + plugin-react 6**, sin cambiar aún React.
6. **Paso 5 — React 19 + Router 7.** Corregir `ref`/`forwardRef` y types.
7. **Paso 6 — Sustituir Quill; decidir Flowbite vs diseño propio.**
8. **Paso 7 — Tailwind 4** (opcional, aislado).

Cada paso: build Docker + migraciones + recorrido login → biblioteca → ficha de libro.

### 1.4 Riesgos de seguridad ligados a dependencias y config (hoy)

- `SECRET_KEY` con fallback `django-insecure-key-change-this`.
- `DEBUG` parseado con `int()`: un `.env` con `true`/`True` rompe el arranque.
- JWT persistido en **localStorage** (`zustand/persist`, clave `auth-storage`) → XSS = sesión robada.
- `console.log` de tokens en `api.ts` y `store/auth.ts`.
- Channels usa `AuthMiddlewareStack` (sesión cookie), **no JWT**. El SPA autentica con Bearer: el WebSocket de chat **no encaja** con el login actual.
- Enrichment de portadas/fotos desde URLs remotas **sin validar** tipo/tamaño (SSRF / bombas de imagen).
- `ImportBookView` y `AuthorDetailView` hacen HTTP síncrono en el request: fácil de abusar (DoS).
- Google OAuth en UI (`/auth/google`) **no existe** en el backend Django activo.

---

## Fase 2 — Refactorización y arquitectura

### 2.1 Deuda estructural

**Código muerto / doble stack**

- `backend/app/` y `backend/config/` son un **esqueleto FastAPI/SQLAlchemy** (mencionado en `.gitignore` como “Python / FastAPI”). El runtime real es `mybookconnect` + `manage.py`.
- `backend/messages/apps.py` vs app real `messages_app`.
- Conversaciones se movieron de `users` (migraciones 0005/0006) a `messages_app`. Correcto, pero conviene documentarlo y no dejar tests huérfanos (`test_*.py` en raíz de backend).

**Modelos Django**

- `Book.created_at` usa `datetime.utcnow` (ingenuo, sin TZ) pese a `USE_TZ = True`. Debe ser `auto_now_add=True` o `timezone.now`.
- `USE_L10N = True` está **deprecado** desde Django 4.0 y sobra en 5/6.
- `unique_together` en `UserBook` → `UniqueConstraint`.
- `Conversation.Meta.unique_together = ('id',)` no aporta unicidad de participantes (se pueden duplicar chats 1:1).
- Un libro tiene **un solo autor** (`ForeignKey`). La realidad editorial es M2M.
- `Review` y `UserBook.notes/rating` se duplican vía signals: fácil desincronizar y mata el `average_rating` con `book.save()` completo (riesgo de bucles y escrituras extra).
- Ratings 1–10 sin `MinValueValidator`/`MaxValueValidator`.
- `Author.name` sin unicidad ni `slug`; `get_or_create(name=)` genera duplicados (“J.K. Rowling” vs “JK Rowling”).
- Señales de rating en un lado del conflicto; `Errata` en el otro: hay que **fusionar ambos**.

**API REST**

- Mezcla de `generics` y `APIView` sueltos; no hay `ViewSet` + router (salvo el intent de chat en un lado del conflicto).
- Sin paginación global (sí en UserBook); listados de libros/autores pueden crecer sin control.
- Sin `django-filter`; filtros ad hoc en `get_queryset`.
- Permisos: casi todo `IsAuthenticated`. Falta `IsOwnerOrReadOnly`, rol editor como `permission`, throttle en import/enrichment.
- `users.urls` se incluye **dos veces** (`api/v1/auth/` y `api/v1/users/`): rutas duplicadas y confusas.
- Enrichment en `retrieve()`: viola separación de responsabilidades (lectura vs job). Mover a Celery / Django-Q / task on-commit.
- Recomendaciones actuales = “misma categoría, no leídos, top rating”. Válido como v1; no es IA.

**Frontend React**

- `Home.tsx` es un placeholder (“Próximamente”).
- Cliente HTTP fragmentado: `authApi` (fetch + URL hardcodeada `localhost:8000`) vs `fetch` + `VITE_API_URL` en el store. Axios instalado y vacío.
- Token en persistencia sin refresh automático (`/token/refresh/` existe y no se usa).
- Componentes duplicados: `EditProfile` en `components/` y `pages/`; `login.tsx` vs `LoginModal`.
- Lazy routes a medias y rotas por el conflicto de `App.tsx`.
- Flowbite + Tailwind teal de 2024; sin design tokens ni dark mode.
- `Friends` asume `/users/:id`; `App` no está unificado.

### 2.2 Refactorizaciones propuestas (por oleadas)

**Oleada A — Unificar dominio**

- Resolver conflictos.
- Conservar: User (`blocked_users` + `is_editor`), Book/Author/Category, UserBook, Review, Errata, Conversation/Message.
- Extraer signals de rating a `books/signals.py` y `update_fields=['average_rating']`.
- Constraint: una Review por (user, book) alineada con UserBook **o** eliminar Review y exponer notas como reseña.

**Oleada B — API limpia**

- Un solo montaje de URLs: `/api/v1/auth/*`, `/api/v1/users/*`, `/api/v1/books/*`, `/api/v1/messages/*`.
- ViewSets + `DefaultRouter`.
- `drf-spectacular` para OpenAPI; el frontend deja de adivinar contratos.
- Throttling `import` / `enrich`.
- JWT en WebSocket (`channels` + middleware que lea `?token=` o cabecera tras handshake).
- Paginación default + `ordering`/`search` con DRF.

**Oleada C — Capa de cliente**

- `src/api/client.ts`: base URL `import.meta.env.VITE_API_URL`, interceptores de 401 → refresh, sin logs de secretos.
- TanStack Query para biblioteca, ficha, amigos.
- Zustand solo para sesión (mejor: memoria + cookie httpOnly a medio plazo).

**Oleada D — Dominio de catálogo**

- Job asíncrono de enrichment; la GET no llama a Wikipedia.
- Deduplicar autores (normalizar nombre + Wikidata Q-id).
- Autores múltiples por libro.

### 2.3 Docker y Compose

**Dockerfile backend**

- Etapas `development` y `production` son **idénticas** (mismo `CMD` Daphne, copia total del árbol).
- No hay `pip` hash / `uv.lock`.
- Corre como **root**.
- No hay `HEALTHCHECK`.
- Se copia `.env`, tests y media al contexto (revisar `.dockerignore`; puede no existir).

**Dockerfile frontend**

- La etapa `production` **parte de `development`**, que ya instaló deps de desarrollo y copió fuentes: imagen de build inflada. Patrón correcto: `deps` → `build` → `nginx` (sin pnpm ni src).
- Nginx 1.25 (línea vieja); no hay `nginx.conf` (SPA fallback `/index.html`, cabeceras de seguridad, cache de hashed assets).
- `pnpm install --no-frozen-lockfile` oculta drift del lockfile.

**docker-compose.yml (dev)**

- Sin `healthcheck` ni `depends_on: condition: service_healthy` (el API arranca antes que Postgres).
- Puertos de **Postgres y Redis publicados** al host (5432, 6379): innecesario y peligroso.
- Sin `restart: unless-stopped`.
- Backend no declara `target`; usa la última etapa del Dockerfile (development/production según orden). Hoy la última es `development`, frágil.
- Redis sin persistencia ni password (ok en local; mal si se copia a prod).
- `DEBUG`/hosts asumen red Docker (`HOST=db`, `cache`).

**docker-compose.prod.yml**

- **Inválido/incompleto:** no tiene `build.context`, `env_file`, volúmenes, db, redis ni red. No se puede desplegar tal cual.
- Publica `8000` del API al mundo; debería estar detrás de un reverse proxy (Caddy/Traefik/Nginx) con TLS.
- Media y estáticos no definidos.

**Prácticas objetivo**

- `.dockerignore` en backend y frontend.
- Usuario no-root (`USER` 1000).
- Dev: Compose con healthchecks, bind mounts, Daphne o `runserver` + Channels.
- Prod: multi-stage real; API (Daphne o Gunicorn+Uvicorn) + worker de tareas + Postgres 16 + Redis; frontend Nginx; **no** publicar DB; secretos por env, nunca imagen.
- Quitar `version: '3.9'` (obsoleto en Compose v2).

---

## Fase 3 — Mejoras de IA y UX social

### 3.1 Qué hay hoy (no es un stack de IA)

El “enriquecimiento” en `books/services.py` es **ETL síncrono** contra Google Books, Open Library, Wikidata y Wikipedia: biografía, foto, portada, categorías. No hay embeddings, ranking aprendido ni agente.

Las “recomendaciones” (si se conserva el lado A del conflicto) son **filtrado por categoría + rating**.

### 3.2 Herramientas modernas propuestas

Objetivo: utilidad real para lectores, **sin** atar el producto a una sola nube.

| Capacidad | Enfoque recomendado | Alternativa local |
| --- | --- | --- |
| Embeddings de descripción/reseña | `pgvector` en Postgres + modelo `intfloat/multilingual-e5-small` (ES/EN) | Ollama + `nomic-embed-text` |
| “Más como este” | k-NN sobre embeddings de `Book.description` | Misma consulta SQL `<=>` |
| Búsqueda semántica | Endpoint `/books/search?q=` híbrido (trigram + vector) | — |
| Agente de biblioteca | Agente con herramientas: buscar catálogo, añadir a wishlist, resumir reseñas | **Ollama** (`llama3.2` / `qwen2.5`) vía `ollama` Docker; en prod opcional OpenAI-compatible |
| Moderación de chat/erratas | Clasificador pequeño o API de moderación | Llama-guard local |
| Deduplicar autores/libros | Embeddings de nombre + ISBN + Q-id | Script periódico, no en el request |

**Arquitectura sugerida (cuando se implemente):**

- Cola (Celery Redis o **Django-tasks** / Huey) para: descargar portadas, embeddings, import masivo.
- Nunca llamar al LLM en el `retrieve` de un libro.
- Capa `books/ai/` aislada del resto de la API (el frontend solo consume resultados).
- Presupuesto: empezar por **pgvector + e5-small**; el agente local es fase posterior.

### 3.3 UX de red social — huecos y propuestas

**Huecos actuales**

- Home no es un feed.
- No hay actividad (quién leyó X, nuevas reseñas de amigos).
- Chat backend existe; no hay inbox en el header.
- Follow es unidireccional; “Amigos” es una lista.
- Privacidad por campo está en el modelo; hay que auditar que el serializer la respete siempre.
- Bloqueo (línea A) no está integrado en chat.
- Sin notificaciones.
- Sin clubs / estanterías públicas / “actualmente leyendo”.
- Perfil y biblioteca ajenos poco “sociales” (no se ve qué lees en común).

**Mejoras de producto (prioridad)**

1. **Feed de Home:** reseñas de gente que sigues + libros añadidos esta semana + recomendaciones (categoría ahora; embeddings después).
2. **Estado “leyendo / leído / quiero”** visible en la ficha y en el perfil (ya está en UserBook; falta UI social).
3. **Inbox:** badge de no leídos, lista de conversaciones, WebSocket con JWT.
4. **Notificaciones in-app:** follow, mensaje, “ha reseñado un libro que tienes”.
5. **Libros en común** en perfil ajeno.
6. **Erratas** (línea B): flujo claro usuario → editor; no mezclar con el perfil público.
7. **Búsqueda global** (libros, autores, usuarios) en el header.
8. **Onboarding:** 3 géneros + 5 libros para sembrar el feed.
9. **Accesibilidad y móvil:** contraste teal-800, foco, tamaños táctiles; verificar viewport pequeño.
10. **OAuth real** (Google) o quitar el botón que apunta a una ruta inexistente.

---

## Hoja de ruta sugerida tras aprobación

| Orden | Entrega | Criterio de hecho |
| --- | --- | --- |
| 0 | Resolver conflictos y rutas | `docker compose up` + login + biblioteca |
| 1 | Higiene deps y secretos | Sin jose/axios muerto; sin log de JWT; media fuera de git |
| 2 | Docker saneado (dev) | Healthchecks, `.dockerignore`, Python 3.13 |
| 3 | Django 5.2 LTS + DRF actual | Migraciones, admin, import de un libro |
| 4 | Cliente API único + refresh JWT | 401 no tira la sesión en silencio |
| 5 | React 19 + Vite 8 | Build prod Nginx con `try_files` |
| 6 | Extraer enrichment a tarea | GET de ficha < 200 ms sin red externa |
| 7 | Feed Home + inbox mínimo | Uso diario plausible |
| 8 | (Opcional) Django 6.1.1 | Misma suite de humo |
| 9 | (Opcional) pgvector + “similares” | Endpoint documentado en OpenAPI |
| 10 | (Opcional) agente Ollama | Solo si 7–9 están estables |

---

## Qué no se ha hecho

- No se ha tocado código de aplicación (salvo este informe).
- No se ha ejecutado `pip-audit` / `pnpm audit` dentro de contenedores (recomendable en el paso 1).
- No se ha verificado la UI en navegador: el árbol actual **no debería arrancar** con los conflictos.

Cuando apruebes este artefacto, indica por qué paso quieres empezar (recomendado: **Paso 0, conflictos**).
