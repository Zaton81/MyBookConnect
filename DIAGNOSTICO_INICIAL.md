# Diagnóstico Técnico y Arquitectónico Inicial — MyBookConnect

**Fecha:** Septiembre 2026  
**Rol:** Lead Software Engineer & Software Architect  
**Fuente de análisis:** Código real del repositorio vs. `ROADMAP.md`  
**Branch:** `develop` | **Commit SHA:** `1b53c1f72f86fcaac7f620142944a80cff128fff`  

---

## 1. Estado Actual

El repositorio alberga una plataforma de lectura social estructurada como monorepo:
* **Backend:** Django 5.2.17 LTS, Django REST Framework 3.18.1, PostgreSQL 16 (contenedor `booksocial-db`), Redis 7 (contenedor `booksocial-cache`), Django Channels 4.2 + Daphne (WebSockets), `djangorestframework-simplejwt` 5.4, `drf-spectacular` 0.28.
* **Frontend:** React 18.3, TypeScript 5.9, Vite 6.4.3, Tailwind CSS 3.4, Flowbite-React 0.7, Zustand 5.0 (autenticación), TanStack Query 5.102, TipTap 3.31.
* **Infraestructura:** `docker-compose.yml` con 4 servicios (`backend`, `db`, `cache`, `frontend`), Dockerfiles multi-stage con usuario no-root (`appuser`), redes internas aisladas, Nginx para SPA con gzip.
* **Volumen de datos en base de datos real:**
  * Usuarios: 12
  * Autores: 147
  * Libros: 226
  * Entradas de biblioteca (`UserBook`): 39
  * Reseñas (`Review`): 15

---

## 2. Arquitectura Detectada

* **Backend:**
  * `mybookconnect/`: Configuración principal del proyecto (`settings.py`, `asgi.py`, `wsgi.py`, `urls.py`).
  * `users/`: Modelo `User` personalizado (hereda de `AbstractUser`), campos de perfil (avatar, biografía, fecha de nacimiento, privacidad `public`/`private`/`friends`, roles `is_editor`, relaciones de seguimiento `following` y usuarios bloqueados `blocked_users`).
  * `books/`: Modelos `Author`, `Book`, `Category`, `UserBook`, `Review`, `Errata`. Servicios de enriquecimiento y descarga (`services.py`), endpoints estándar (`views.py`) y endpoints de IA desacoplados (`ai_views.py`, `ai_service.py`).
  * `messages_app/`: Modelos `Conversation`, `Message`. Consumer WebSocket `ChatConsumer` con autenticación JWT sobre Channels.
* **Frontend:**
  * Estructura centrada en `src/pages/` (`Home`, `Library`, `AddBook`, `BookDetail`, `Author`, `Profile`, `EditProfile`, `Friends`, `Chat`, `pages/legal/`) y `src/components/` (`header`, `footer`, `CookieBanner`, `AmazonAdSlot`, `AIAssistantModal`, etc.).
  * Cliente API unificado (`client.ts`) con gestión de interceptores y auto-refresh de JWT ante 401.

---

## 3. Diferencias Respecto a `ROADMAP.md`

| Aspecto | Definición en `ROADMAP.md` | Estado Real en el Repositorio |
|---|---|---|
| **Tareas Asíncronas** | Celery + Redis para trabajo pesado y llamadas externas | Celery **no está instalado ni configurado**. Redis solo se usa para Channels. |
| **Separación UserBook/Review** | `UserBook` = relación privada; `Review` = opinión pública con `UniqueConstraint(user, book)` | `UserBook` contiene `rating` y `notes`. Signals sincronizan y destruyen `Review` al alterar `UserBook`. |
| **Estados de Lectura** | `ReadingStatus` enum (`want_to_read`, `reading`, `read`, `abandoned`), progreso de páginas | Solo booleano `is_read` y booleano `wishlist`. |
| **Deduplicación e ISBN** | Normalización de ISBN y constraints de unicidad | `isbn` es un `CharField(max_length=30)` sin validación de formato ni normalización de guiones. |
| **Búsqueda** | PostgreSQL Full-Text Search / pg_trgm con fallback semántico | Búsqueda estándar basada en `icontains` en SQL básico. |
| **Tooling de Calidad** | Ruff, Mypy, Pytest, Pytest-Django, Coverage, Pre-commit | **Ausente**. Se usa `manage.py test` estándar (0 tests descubiertos). |
| **CI/CD** | Workflows en `.github/workflows/` (backend, frontend, security) | El directorio `.github/` **no existe**. |
| **Caché en Django** | Redis como backend de caché (`CACHES` en `settings.py`) | Django usa caché en memoria local por defecto; Redis no está configurado en `CACHES`. |

---

## 4. Clasificación de Problemas por Prioridad

### 🔴 Prioridad P0 (Crítico / Bloqueante)
1. **[P0-1] Acoplamiento destructivo entre `UserBook` y `Review` (Fase 3):**
   * *Problema:* Las signals `sync_userbook_to_review` y `delete_review_on_userbook_delete` en `books/models.py` sobrescriben o eliminan reseñas públicas cuando el usuario edita o borra su libro en la biblioteca.
   * *Riesgo:* Pérdida de opiniones y reseñas públicas redactadas por usuarios.
   * *Ausencia de constraint:* `Review` no tiene `UniqueConstraint(fields=['user', 'book'])` a nivel de base de datos.
2. **[P0-2] Ausencia total de suite de pruebas automatizadas y tooling (Fases 0, 1 y 2):**
   * *Problema:* `python manage.py test` reporta `Ran 0 tests`. Los tests existentes son scripts sueltos (`test_privacy.py`, etc.) que operan contra la base de datos viva.
   * *Riesgo:* Cualquier refactor del modelo de datos no tiene red de seguridad automatizada.
3. **[P0-3] Falta de baseline y backup formal del estado de datos (Fase 0):**
   * *Problema:* No existe snapshot ni tag `pre-refactor` de la base de datos de PostgreSQL (12 usuarios, 226 libros, 39 UserBooks, 15 Reviews).

### 🟡 Prioridad P1 (Importante)
4. **[P1-1] Estado de lectura limitado (Fase 4):**
   * *Problema:* Solo existen flags booleanos `is_read` y `wishlist`, imposibilitando reflejar estados como "leyendo actualmente" o "abandonado", ni porcentaje de avance.
5. **[P1-2] Inconsistencias de ISBN y deduplicación (Fase 5):**
   * *Problema:* Falta de normalización de ISBN (guiones, espacios, validación de checksum ISBN-10 / ISBN-13).
6. **[P1-3] Ausencia de paginación por defecto en DRF:**
   * *Problema:* Endpoints como `/api/v1/books/` devuelven listados completos, lo que degradará el rendimiento conforme crezca el catálogo.
7. **[P1-4] Autorización en WebSocket y Chat con usuarios bloqueados:**
   * *Problema:* `ChatConsumer` comprueba que el usuario pertenezca a la conversación, pero no verifica en tiempo real si ha sido bloqueado por el otro participante.
8. **[P1-5] Configuración de Caché en Django:**
   * *Problema:* El servicio Redis está levantado, pero Django no lo tiene configurado en `CACHES`.
9. **[P1-6] Ausencia de Celery para llamadas externas pesadas:**
   * *Problema:* Las consultas externas a Google Books y Wikipedia ocurren de forma síncrona en requests HTTP (aunque mitigadas con `enrichment_attempted`).

### 🟢 Prioridad P2 (Mejora Futura)
10. **[P2-1] Full-Text Search con PostgreSQL (`pg_trgm` / FTS):**
    * Evolucionar la búsqueda de `icontains` a índices trigram y ranking de relevancia.
11. **[P2-2] Motor de recomendaciones híbrido:**
    * Basado en similitud social, géneros leídos y embeddings locales.
12. **[P2-3] Tipado estricto en frontend y eliminación progresiva de `any`.**

---

## 5. Tests Existentes vs. Tests Faltantes

* **Tests existentes:**
  * `backend/test_privacy.py`: Prueba permisos de perfil, follow y bloqueos usando `APIRequestFactory`.
  * `backend/test_enrichment.py`: Prueba importación y enriquecimiento con Wikipedia/Google Books.
  * `backend/test_social.py`: Prueba de endpoints sociales.
  * `backend/test_author_refresh.py`: Prueba de actualización de autor y fotos.
* **Tests faltantes:**
  * Tests formales con `pytest` y base de datos aislada para modelos `UserBook` y `Review`.
  * Tests de integridad referencial (`UniqueConstraint`).
  * Tests de autenticación JWT y refresh rotation.
  * Tests de Channels WebSocket (conexión, mensajes, usuarios bloqueados).
  * Tests unitarios y de componentes en frontend (Vitest + React Testing Library).

---

## 6. Plan de Ejecución Ordenado (Adaptado a la Realidad del Código)

Siguiendo el mandato de *estabilizar primero, consolidar el dominio después*:

### Bloque 1: Estabilización y Calidad (Fase 0 + Fase 1 + Fase 2)
1. **Fase 0: Congelación y Backup**:
   * Confirmar commit HEAD y crear tag `pre-refactor-baseline`.
   * Ejecutar backup completo de PostgreSQL (`pg_dump`) y de la carpeta `media/`.
   * Validar consistencia de migraciones actuales (`makemigrations --check`).
2. **Fase 1: Tooling de Calidad en Backend**:
   * Instalar y configurar `pytest`, `pytest-django`, `pytest-cov`, `ruff`, `mypy`.
   * Crear `pytest.ini` o configuración en `pyproject.toml`.
   * Convertir los scripts sueltos en una suite de tests estándar bajo `backend/tests/`.
   * Configurar scripts de linting y formateo con Ruff.
3. **Fase 2: Tooling de Calidad en Frontend & CI/CD**:
   * Configurar scripts de `lint`, `typecheck`, `test` con `vitest`.
   * Crear `.github/workflows/` (`backend.yml`, `frontend.yml`).

### Bloque 2: Consolidación del Modelo de Dominio (Fase 3, 4 y 5)
4. **Fase 3: Separación segura de `UserBook` y `Review`**:
   * Añadir `UniqueConstraint(user, book)` a `Review` garantizando idempotencia.
   * Migrar de forma segura los datos existentes de `UserBook.rating` y `UserBook.notes` hacia `Review` (sin duplicar ni perder información).
   * Desactivar las signals destructivas `sync_userbook_to_review` y `delete_review_on_userbook_delete`.
   * Actualizar serializers, vistas y frontend para consultar `Review` de manera desacoplada.
5. **Fase 4: Estados de lectura estructurados (`ReadingStatus`)**:
   * Introducir enum `ReadingStatus` (`want_to_read`, `reading`, `read`, `abandoned`) y progreso de páginas.
6. **Fase 5: Normalización y deduplicación de ISBN**.
