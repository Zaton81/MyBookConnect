# Calidad Avanzada, Contratos OpenAPI, Seguridad y Benchmarks — MyBookConnect

Este documento consolida la arquitectura de calidad integral implementada en la **Fase 33** de MyBookConnect, cubriendo validación de contratos OpenAPI 3.0, flujos de integración extremo a extremo (E2E), verificación de guardrails de seguridad (IDOR, inyección XSS, JWT), erradicación de consultas N+1 con complejidad $O(1)$ y pruebas de carga concurrente.

---

## 1. Arquitectura de Calidad y Pilares

La plataforma se valida mediante cuatro suites especializadas en backend y una herramienta reproducible de pruebas de carga:

```
                               ┌───────────────────────────────────────────┐
                               │           Fase 33: Calidad Avanzada       │
                               └─────────────────────┬─────────────────────┘
                                                     │
         ┌───────────────────┬───────────────────────┼───────────────────────┬───────────────────┐
         │                   │                       │                       │                   │
┌────────▼────────┐ ┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐ ┌────────▼────────┐
│ OpenAPI Contract│ │  E2E User Flow  │     │Security Hardening│     │ Query Benchmarks│ │ Load & Concurrency│
│  drf-spectacular│ │ Registro a Feed │     │  IDOR, XSS, JWT │     │   Cero N+1 O(1) │ │ RPS, p95/p99 SLAs │
└─────────────────┘ └─────────────────┘     └─────────────────┘     └─────────────────┘ └─────────────────┘
```

---

## 2. Contratos de API OpenAPI (`test_phase33_openapi_contract.py`)

Verifica que el esquema vivo servido en `/api/schema/` coincida fielmente con los modelos y respuestas reales de DRF:

1. **Rutas Clave Registradas:**
   - Catálogo general y detalle: `/api/v1/books/`, `/api/v1/books/{id}/`.
   - Plataforma de Autores: `/api/v1/books/authors/`, `/api/v1/books/authors/claim/`, `/api/v1/books/authors/dashboard/`.
   - Afiliación ética multiformato: `/api/v1/books/{id}/affiliate-links/`.
   - Muro social: `/api/v1/auth/users/{user_id}/posts/` o `/api/v1/users/{user_id}/posts/`.
   - Reseñas de perfil: `/api/v1/users/{user_id}/reviews/`.
2. **Esquemas Tipados en `components/schemas`:**
   - Modelos base: `Book`, `Review`, `User`, `UserBasic`, `ReadingList`, `ReadingListItem`.
   - Respuestas de interacción: `ReviewComment`, `ReviewLikeToggleResponse`, `ReadingStatsResponse`, `AIStatusResponse`.
3. **Validación de Respuestas Reales:**
   - `test_book_api_response_adheres_to_contract`: Comprueba que `GET /api/v1/books/` devuelva la estructura de autor, coautores (`authors`), ISBN normalizado y enlaces de afiliación en endpoint dedicado.
   - `test_user_post_api_response_adheres_to_contract`: Comprueba que las publicaciones del muro entreguen `author`, `target_user`, `book`, `likes_count`, `comments_count` y `user_has_liked`.

---

## 3. Flujo Extremo a Extremo (E2E User Journey) (`test_phase33_e2e_user_journey.py`)

Simula de forma continua el viaje completo de dos usuarios interactuando en la plataforma:

1. **Paso 1: Registro y Autenticación:** Registro de Alice (`/api/v1/auth/register/`) y login JWT (`/api/v1/auth/token/`).
2. **Paso 2: Onboarding Literario:** Selección de géneros favoritos (`favorite_categories`) y meta anual de libros (`reading_goal_books`).
3. **Paso 3: Descubrimiento de Catálogo:** Búsqueda full-text en `/api/v1/books/?search=...` y consulta de opciones de compra de afiliado en `/api/v1/books/{id}/affiliate-links/`.
4. **Paso 4: Biblioteca Personal:** Adición de libro a la estantería (`UserBook`) con estado `reading` y avance de página.
5. **Paso 5: Reseña y Calificación:** Publicación de reseña de 5 estrellas con título y texto en `/api/v1/reviews/`.
6. **Paso 6: Muro Social del Perfil:** Creación de publicación en el muro (`/api/v1/users/<id>/posts/`) vinculando el libro leído.
7. **Paso 7: Interacción Social de Bob:**
   - Registro y login de Bob.
   - Follow a Alice (`/api/v1/users/<alice_id>/follow/`).
   - Visualización del muro de Alice.
   - Like en la publicación (`/api/v1/users/posts/<post_id>/like/`).
   - Comentario sanitizado en la publicación (`/api/v1/users/posts/<post_id>/comments/`).
   - Comprobación de que la actividad social se refleja en el feed unificado (`/api/v1/auth/feed/`).

---

## 4. Blindaje de Seguridad y Resiliencia (`test_phase33_security_hardening.py`)

1. **Protección IDOR (Insecure Direct Object Reference):**
   - Un usuario atacante no puede eliminar posts de muro creados por otro usuario (retorna `403 Forbidden`).
   - Un usuario no puede alterar ni borrar reseñas de otros lectores (`403 Forbidden` / `404 Not Found`).
   - Un usuario no puede modificar el estado de lectura de la biblioteca ajena (`403 Forbidden`).
2. **Sanitización contra Inyección y XSS:**
   - Payloads que incluyen etiquetas `<script>` o eventos `onerror` son sanitizados por `html_sanitizer.py`, asegurando que el contenido persistido y serializado no contenga código ejecutable.
3. **Seguridad JWT:**
   - Tokens con firma alterada o malformada devuelven inmediatamente `401 Unauthorized`.
   - Tokens enviados a la lista negra tras logout (`/api/v1/auth/logout/`) son invalidados para cualquier renovación subsiguiente.
4. **Fronteras de Privacidad y Bloqueos:**
   - Si un usuario bloquea a otro, el usuario bloqueado no puede acceder a las publicaciones del muro ni reseñas del bloqueador (`404 Not Found` según la directiva de confidencialidad de MyBookConnect).
5. **Restricción a Peticiones No Autenticadas:**
   - Cualquier intento de mutación (creación de posts, likes o comentarios) sin encabezado de autorización devuelve `401 Unauthorized`.

---

## 5. Prevención de N+1 y Benchmarks de Consultas (`test_phase33_query_benchmarks.py`)

Se utiliza `CaptureQueriesContext(connection)` para garantizar formalmente que las consultas SQL sean estrictamente constantes $O(1)$:

### Optimizaciones Clave Resueltas en la Fase 33:
- **`Book.get_author_names()`:** Al llamar a `self.authors.values_list(...)`, Django ignoraba el prefetch en memoria y lanzaba 1 consulta SQL por cada libro renderizado. Se optimizó comprobando `_prefetched_objects_cache`:
  ```python
  if hasattr(self, '_prefetched_objects_cache') and 'authors' in self._prefetched_objects_cache:
      author_names = [a.name for a in self.authors.all()]
  else:
      author_names = list(self.authors.values_list('name', flat=True))
  ```
- **`UserPostSerializer.get_user_has_liked()`:** Se optimizó verificando si `likes` está en el prefetch cache para evitar ejecutar `obj.likes.filter(...)` por cada post del muro.
- **`UserPostListCreateView`:** Se configuró `.select_related('author', 'target_user', 'book', 'book__author').prefetch_related('likes', 'comments__user', 'book__authors')`.
- **`ReviewSerializer` & `BookSerializer`:** Se cachearon en el ciclo de vida de la petición `request._cached_following_ids`, `request._rating_dist_{id}` y `request._reviews_count_{id}`, garantizando que renderizar múltiples reseñas del mismo libro no duplique el cálculo de distribución de estrellas.

### Resultados de los Tests:
| Endpoint Evaluado | Consultas (Volumen Pequeño) | Consultas (Volumen Grande) | Complejidad | Estado |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/users/<id>/posts/` | 8 queries (2 posts) | 8 queries (8 posts) | **O(1) Constante** | **PASÓ** |
| `GET /api/v1/reviews/?book=<id>` | 10 queries (2 reviews) | 10 queries (8 reviews) | **O(1) Constante** | **PASÓ** |
| `GET /api/v1/auth/feed/` | 4 queries | 4 queries | **O(1) Constante** | **PASÓ** |

---

## 6. Pruebas de Carga y Medición de SLAs (`scripts/load_testing/load_test_benchmark.py`)

Script autónomo para evaluar concurrencia (hilos concurrentes, RPS y percentiles de latencia p50, p95, p99).

### Ejecución:
```bash
# Modo reporte estándar (desarrollo):
python scripts/load_testing/load_test_benchmark.py --host http://localhost:8000 --concurrency 5 --requests 20

# Modo estricto para CI/CD y producción:
python scripts/load_testing/load_test_benchmark.py --host http://localhost:8000 --concurrency 10 --requests 50 --strict
```

### Resultados Medidos en Entorno Local:
```text
--- Probando: Health Check (http://localhost:8000/api/v1/health/) ---
Concurrencia: 5 hilos | Peticiones totales: 10
RPS: 86.71 | Éxito: 100.0%
Media: 49.15ms | p50: 53.76ms | p95: 60.03ms | p99: 60.03ms
SLA p95 objetivo: <= 100.0ms -> [DENTRO DE SLA]

--- Probando: Catálogo de Libros (http://localhost:8000/api/v1/books/) ---
Concurrencia: 5 hilos | Peticiones totales: 10
RPS: 18.40 | Éxito: 100.0%
Media: 268.43ms | p50: 269.90ms | p95: 280.97ms | p99: 280.97ms
SLA p95 objetivo: <= 300.0ms -> [DENTRO DE SLA]
```

---

## 7. Instrucciones para Ejecutar las Pruebas

```bash
# Ejecutar suite específica de Calidad Avanzada (Fase 33):
docker compose exec -T backend pytest tests/test_phase33_*.py -v

# Ejecutar suite de regresión completa de backend:
docker compose exec -T backend pytest tests/test_phase13_*.py tests/test_phase26_*.py tests/test_phase27_*.py tests/test_phase28_*.py tests/test_phase29_*.py tests/test_phase30_*.py tests/test_phase31_*.py tests/test_phase32_*.py tests/test_phase33_*.py -v

# Ejecutar verificación de frontend:
cd frontend && pnpm test && pnpm typecheck
```
