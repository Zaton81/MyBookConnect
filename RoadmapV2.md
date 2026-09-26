# MyBookConnect — Roadmap maestro

> **Documento de planificación técnica y de producto**
>
> Última revisión: 20 de septiembre de 2026
>
> Repositorio: `https://github.com/Zaton81/MyBookConnect`
>
> Estado objetivo de este documento: llevar MyBookConnect desde su estado actual hasta una **beta cerrada sólida, segura, observable y preparada para crecer**, evitando añadir complejidad de producto antes de resolver privacidad, integridad, calidad, seguridad y operación.

---

# 0. Propósito

Este documento sustituye al roadmap anterior y debe considerarse la **fuente de planificación principal** del proyecto.

El objetivo no es desarrollar funcionalidades indefinidamente. El objetivo es avanzar por fases verificables hasta conseguir:

1. una arquitectura coherente;
2. un dominio de datos consistente;
3. privacidad correcta en todas las superficies sociales;
4. autenticación y autorización robustas;
5. búsquedas y recomendaciones escalables;
6. IA controlada por costes y seguridad;
7. frontend y backend con calidad automatizada;
8. despliegue reproducible;
9. observabilidad y capacidad de recuperación;
10. una beta cerrada con usuarios reales;
11. una base preparada para iterar según datos reales.

## Regla fundamental

**No añadir una funcionalidad nueva si existe una deuda P0/P1 que pueda comprometer seguridad, privacidad, integridad de datos, estabilidad o capacidad de desplegar.**

---

# 1. Estado actual del proyecto

La revisión actual del repositorio muestra una plataforma full-stack considerablemente evolucionada.

El README actual describe:

- React 18 + Vite + TypeScript;
- Django 5.2 + Django REST Framework;
- PostgreSQL 16;
- Redis 7;
- Celery;
- Django Channels + Daphne;
- JWT con rotación y blacklist;
- búsqueda con `pg_trgm`;
- biblioteca personal;
- reseñas separadas de `UserBook`;
- seguimiento social;
- bloqueos;
- privacidad granular;
- mensajería WebSocket;
- recomendaciones;
- feedback de recomendaciones;
- IA;
- observabilidad;
- Docker;
- documentación técnica;
- pruebas backend y frontend.

El repositorio actual contiene además `docs/`, ADRs, scripts, configuración Docker, documentación y un roadmap previo.

## 1.1. Diagnóstico global

### Fortalezas actuales

- Arquitectura desacoplada frontend/backend.
- Separación razonable por dominios.
- PostgreSQL como fuente de verdad.
- Redis para caché, rate limiting y Channels.
- Celery para trabajo asíncrono.
- Uso de `select_related`/`prefetch_related` en partes del backend.
- Sistema de recomendaciones ya versionado.
- Captura de feedback de recomendaciones.
- Soft delete.
- Modelo de biblioteca personal más rico que en la versión inicial.
- Separación conceptual entre biblioteca (`UserBook`) y reseña pública (`Review`).
- Sistema de privacidad y bloqueos.
- Observabilidad y logging estructurado.
- Docker y composición de servicios.
- Documentación técnica y ADRs.
- Suite de pruebas backend y frontend.
- Preparación para IA mediante proveedores intercambiables.

## 1.2. Riesgos actuales prioritarios

La revisión actual identifica especialmente:

### P0 — Privacidad social

Hay superficies como feed, `ReadingMatch`, usuarios similares y recomendaciones que deben comprobar de forma consistente:

- privacidad del perfil;
- visibilidad de actividad;
- bloqueos bidireccionales;
- relación de seguimiento;
- visibilidad de reseñas;
- visibilidad de listas.

No se debe asumir que una restricción aplicada al perfil se aplica automáticamente al resto de endpoints.

### P0 — Fuente de verdad de ratings

Debe quedar inequívocamente definido que:

```text
UserBook = estado personal de lectura
Review   = opinión pública
```

El rating público debe pertenecer a `Review`.

No debe existir una segunda fuente de rating que pueda producir divergencias.

### P1 — WebSocket authentication

Debe eliminarse progresivamente el JWT en query string y consolidar un mecanismo seguro de autenticación para WebSockets.

### P1 — IA

El endpoint de IA debe tener:

- validación estricta;
- límites de tamaño;
- roles permitidos;
- rate limiting específico;
- límites de coste;
- timeout;
- observabilidad;
- protección frente a abuso.

### P1 — Calidad frontend

La documentación actual menciona typecheck y tests, pero los scripts del `package.json` deben quedar alineados con la documentación y CI.

### P1 — Docker / healthchecks

Los healthchecks deben representar correctamente:

```text
liveness
readiness
```

y no utilizar una ruta de documentación OpenAPI como sustituto de la salud de la aplicación.

### P1 — Documentación

Debe existir una única fuente de verdad arquitectónica y eliminar documentación obsoleta o contradictoria.

---

# 2. Principios de desarrollo

## 2.1. Calidad antes que velocidad

Cada fase debe terminar con:

- tests;
- lint;
- typecheck;
- build;
- revisión de seguridad cuando proceda;
- migraciones verificadas;
- documentación actualizada;
- commit;
- push.

## 2.2. Cambios pequeños y reversibles

Preferir:

```text
1 PR
1 objetivo coherente
1 conjunto de cambios
1 validación
```

Evitar:

```text
"ya que estamos, rehago todo el módulo"
```

## 2.3. No romper contratos existentes sin plan

Cuando se cambie:

- endpoint;
- serializer;
- modelo;
- campo;
- WebSocket protocol;
- respuesta JSON;

se debe documentar:

- qué cambia;
- por qué;
- compatibilidad;
- migración;
- estrategia de deprecación.

## 2.4. Privacidad por diseño

La privacidad no pertenece únicamente al endpoint de perfil.

Debe aplicarse en:

- perfiles;
- feed;
- seguidores;
- listas;
- reseñas;
- actividad;
- recomendaciones;
- usuarios similares;
- Reading Match;
- estadísticas;
- notificaciones;
- búsquedas;
- WebSockets.

## 2.5. Server state vs client state

Mantener:

- TanStack Query → server state;
- Zustand → estado global/local de interfaz.

No duplicar innecesariamente datos del servidor en Zustand.

## 2.6. Asincronía

Todo proceso lento o externo debe evaluarse para ejecución mediante Celery:

- proveedores de libros;
- descarga de imágenes;
- embeddings;
- enriquecimiento;
- emails;
- tareas de mantenimiento;
- generación de recomendaciones pesadas.

No realizar llamadas externas lentas en el request path salvo que exista una razón explícita.

## 2.7. Seguridad por defecto

Nunca confiar en:

- frontend;
- headers proporcionados por el cliente;
- roles enviados por el cliente;
- `system` messages enviados por frontend;
- identificadores de usuario sin comprobar permisos;
- flags de privacidad del cliente.

---

# 3. Definición de terminado global

Una fase solo se considera terminada cuando:

- [ ] Código implementado.
- [ ] Migraciones creadas y probadas.
- [ ] Tests nuevos.
- [ ] Tests existentes siguen pasando.
- [ ] Typecheck pasa.
- [ ] Lint pasa.
- [ ] Build frontend pasa.
- [ ] Docker build pasa.
- [ ] Integración relevante validada.
- [ ] OpenAPI actualizada.
- [ ] Documentación actualizada.
- [ ] Logs no exponen secretos.
- [ ] Permisos revisados.
- [ ] Caché invalidada correctamente si aplica.
- [ ] No quedan TODO críticos.
- [ ] Se ha realizado revisión del diff.
- [ ] Commit descriptivo.
- [ ] Push a `develop`.
- [ ] Si la fase es publicable: merge/promoción según política del repositorio.

---

# 4. Estrategia de ramas

Mantener:

```text
main
  ↑
develop
  ↑
feature/*
fix/*
security/*
refactor/*
```

## Política

- `main`: código estable/publicable.
- `develop`: integración.
- `feature/*`: nuevas funcionalidades.
- `fix/*`: correcciones.
- `security/*`: vulnerabilidades.
- `refactor/*`: cambios estructurales sin funcionalidad.

Cada fase importante debe terminar con un commit en `develop`.

No hacer commits gigantes que mezclen:

- migración;
- frontend;
- infraestructura;
- documentación;
- funcionalidades no relacionadas.

---

# 5. FASE 0 — Baseline técnico y auditoría reproducible [COMPLETADA]

**Prioridad: P0 — COMPLETADA**

Objetivo: tener una fotografía reproducible del estado real antes de seguir modificando.

## 5.1. Inventario

- [x] Registrar commit SHA exacto.
- [x] Registrar versiones Python/Django/Node/TypeScript.
- [x] Registrar versiones Docker.
- [x] Registrar dependencias backend.
- [x] Registrar dependencias frontend.
- [x] Registrar servicios Docker.
- [x] Registrar variables de entorno.
- [x] Registrar endpoints.
- [x] Registrar WebSockets.
- [x] Registrar tareas Celery.
- [x] Registrar modelos principales.
- [x] Registrar índices.
- [x] Registrar extensiones PostgreSQL.

## 5.2. Comprobaciones

Ejecutar:

```bash
docker compose config
docker compose ps
docker compose exec -T backend pytest -q
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py makemigrations --check
```

Frontend:

```bash
npm ci
npm run typecheck
npm run test
npm run build
```

Si los scripts no existen, crearlos como parte de esta fase.

## 5.3. Auditoría de documentación

Comparar:

- `README`
- `Roadmap.md`
- `architecture.md`
- `docs/`
- ADRs
- `instruccionesAgente.md`
- Dockerfiles
- compose
- CI

Eliminar contradicciones.

### Entregable

`docs/project-baseline.md` [COMPLETADO]

---

# 6. FASE 1 — Modelo de dominio e integridad de datos [COMPLETADA]

**Prioridad: P0 — COMPLETADA**

Objetivo: eliminar ambigüedades del dominio antes de introducir más funcionalidades.

---

## 6.1. UserBook vs Review

Definición definitiva:

### UserBook

Representa:

> "Mi relación personal con este libro."

Puede contener:

- usuario;
- libro;
- estado;
- progreso;
- páginas;
- fechas;
- formato;
- propiedad;
- wishlist;
- notas privadas.

No debe ser la fuente del rating público.

### Review

Representa:

> "Mi opinión pública sobre este libro."

Contendrá:

- usuario;
- libro;
- rating;
- título;
- texto;
- fecha;
- edición/estado de publicación si aplica;
- moderación;
- likes;
- comentarios.

## 6.2. Rating

Aplicar:

```text
1 <= rating <= 5
```

en:

- modelo;
- serializer;
- API;
- frontend.

Añadir:

- `MinValueValidator(1)`
- `MaxValueValidator(5)`

y tests.

## 6.3. Constraints

Revisar:

- `UniqueConstraint`;
- índices;
- `CheckConstraint`;
- foreign keys;
- cascadas;
- `PROTECT`;
- `SET_NULL`;
- soft delete.

Especialmente:

```text
unique(user, book)
unique(user, review)
unique(user, list, book)
```

cuando corresponda.

## 6.4. Transacciones

Revisar operaciones compuestas:

```text
crear UserBook + evento
crear Review + actualizar caché
follow + notificación
like + contador
comment + notificación
reading progress + analytics
```

Usar:

```python
transaction.atomic()
```

cuando una operación deba ser indivisible.

## 6.5. Soft delete

Definir política única:

- qué modelos usan soft delete;
- qué significa eliminado;
- cuándo se excluyen;
- cómo se restauran;
- qué ocurre con relaciones;
- qué ve el propietario;
- qué ve otro usuario.

## 6.6. Entregable

`docs/domain/data-integrity.md` [COMPLETADO]

### Criterio de salida

- [x] Un único origen de rating.
- [x] Constraints verificadas.
- [x] Migraciones limpias.
- [x] Tests de integridad.
- [x] Ningún endpoint depende de comportamiento ambiguo.

---

# 7. FASE 2 — Privacy Core [COMPLETADA]

**Prioridad: P0 — COMPLETADA**

Objetivo: convertir la privacidad en una política central reutilizable.

---

## 7.1. Crear PrivacyService

Diseñar algo equivalente a:

```text
PrivacyService
├── can_view_profile()
├── can_view_reading_activity()
├── can_view_activity()
├── can_view_review()
├── can_view_list()
├── can_view_followers()
├── can_view_following()
├── can_view_statistics()
├── can_match()
├── can_recommend()
├── can_interact()
└── can_message()
```

No copiar reglas entre views.

## 7.2. Matriz de privacidad

Definir explícitamente:

| Recurso | Público | Seguidores | Privado |
|---|---:|---:|---:|
| Perfil | configurable | configurable | no |
| Bio | configurable | configurable | no |
| Biblioteca | configurable | configurable | no |
| Actividad | configurable | configurable | no |
| Reviews | configurable | configurable | no |
| Listas | configurable | configurable | no |
| Estadísticas | configurable | configurable | no |
| Reading Match | configurable | configurable | no |
| Seguidores | configurable | configurable | no |

La matriz real debe reflejar los campos de configuración existentes.

## 7.3. Bloqueos

Toda interacción debe considerar:

```text
A bloquea B
B bloquea A
```

y nunca asumir que basta con comprobar una dirección.

Casos:

- perfil;
- búsqueda;
- feed;
- recomendaciones;
- usuarios similares;
- mensajes;
- comentarios;
- likes;
- follows;
- match.

## 7.4. Feed

Corregir:

```text
Review.objects...
UserBook.objects...
```

para que el feed solo incluya:

- actividad permitida;
- usuarios visibles;
- usuarios no bloqueados;
- relación social válida;
- contenido público para el receptor.

## 7.5. Reading Match

No comparar directamente bibliotecas privadas.

El cálculo debe usar únicamente información que el usuario pueda legítimamente consultar.

## 7.6. Usuarios similares

Excluir:

- bloqueados por mí;
- usuarios que me han bloqueado;
- perfiles que no permitan descubrimiento;
- usuarios eliminados;
- cuentas suspendidas.

## 7.7. Recomendaciones sociales

No utilizar datos privados para generar una recomendación visible a terceros.

## 7.8. Listas

Comprobar privacidad de:

- lista;
- elementos;
- seguidores;
- comentarios.

## 7.9. Tests obligatorios

Crear una matriz de tests con:

```text
public/public
public/private
friends/friends
private/private
blocked one-way
blocked two-way
deleted user
deactivated user
anonymous
authenticated
owner
follower
non-follower
```

### Entregable
`docs/security/privacy_core.md` [COMPLETADO]

### Criterio de salida

- [x] Cero endpoints sociales sin política explícita de visibilidad.
- [x] PrivacyService centralizado y delegación en policies.
- [x] Configuración granular de visibilidad en User (reading, activity, messages) y UI en frontend.
- [x] Prevención de fuga de datos en serializadores y anti-enumeración 404 ante bloqueo mutuo.
- [x] Suite completa de pruebas en `backend/tests/test_phase02_privacy_core.py` (7/7 tests passed).

---

# 8. FASE 3 — Seguridad de autenticación y autorización [COMPLETADA]

**Prioridad: P0/P1 — COMPLETADA**

## 8.1. JWT

Revisar:

- access token TTL;
- refresh TTL;
- rotación;
- blacklist;
- revocación;
- logout;
- cambio de contraseña;
- password reset;
- dispositivos/sesiones.

## 8.2. WebSocket

Eliminar progresivamente:

```text
ws://...?token=...
```

Preferir:

- cookie HttpOnly/Secure cuando la arquitectura lo permita;
- mecanismo de handshake seguro;
- token de vida corta específico para WebSocket.

Documentar la transición.

## 8.3. Permisos

Auditar cada endpoint:

```text
Authentication
Authorization
Object-level permission
Privacy
Block
Rate limit
```

## 8.4. IDOR

Probar específicamente:

```text
GET /users/{other_id}
PATCH /books/{other_id}
GET /lists/{other_id}
GET /conversations/{other_id}
GET /reviews/{other_id}
```

con usuarios sin permisos.

## 8.5. Subida de archivos

Validar:

- MIME real;
- extensión;
- tamaño;
- dimensiones;
- contenido;
- nombre;
- metadata;
- imágenes corruptas;
- SVG potencialmente peligroso.

## 8.6. Cabeceras

Revisar:

- HSTS;
- CSP;
- X-Content-Type-Options;
- Referrer-Policy;
- Permissions-Policy;
- frame policy;
- cookies Secure/HttpOnly/SameSite.

## 8.7. Secretos

Comprobar:

```text
.env
logs
CI
Docker layers
frontend bundle
OpenAPI
error responses
```

Nunca enviar secretos al frontend.

### Entregable
`docs/security/auth_security.md` [COMPLETADO]

### Criterio de salida
- [x] Revocación instantánea de Access Tokens en vuelo mediante marca temporal en Redis (`RevocationCheckingJWTAuthentication`).
- [x] WebSocket handshake seguro mediante tickets efímeros de uso único (`POST /api/v1/auth/ws-ticket/`).
- [x] Flujo de verificación de correo con remitente `noreply@mybooksocial.com` configurable por entorno.
- [x] Google OAuth 2.0 integrado en backend y frontend (Login y Register con `GoogleLoginButton`).
- [x] Auditoría IDOR y anti-enumeración 404 aplicada en perfiles, listas y lecturas.
- [x] Cabeceras de seguridad HTTP configuradas (`SECURE_REFERRER_POLICY`, `nosniff`, `DENY`).
- [x] Suite de pruebas automatizadas en `tests/test_phase03_auth_security.py` (8/8 tests passed).

---

# 9. FASE 4 — Mensajería y tiempo real [COMPLETADA]

**Prioridad: P1**

## 9.1. Modelo de lectura

Para chats multiusuario, reemplazar:

```text
Message.read
```

por un modelo equivalente a:

```text
ConversationParticipant
├── conversation
├── user
├── last_read_message
└── last_read_at
```

Si el producto va a limitarse estrictamente a 1:1 en beta, documentarlo y mantener el booleano solo si las pruebas garantizan esa restricción.

## 9.2. WebSocket lifecycle

Implementar:

- connect;
- authenticate;
- authorize;
- subscribe;
- send;
- receive;
- disconnect;
- reconnect;
- heartbeat;
- stale connection cleanup.

## 9.3. Idempotencia

Evitar mensajes duplicados cuando el cliente reconecta.

Usar un `client_message_id` si resulta necesario.

## 9.4. Orden

Definir:

- ordering;
- timestamp;
- ID monotónico o equivalente;
- paginación.

## 9.5. Tests

- conexión;
- autenticación;
- autorización;
- bloqueo;
- conversación inexistente;
- mensaje duplicado;
- reconexión;
- Redis caído;
- usuario eliminado.

---

# 10. FASE 5 — IA segura y controlada [COMPLETADA]

**Prioridad: P1**

La IA debe ser una capa opcional y controlada, no una dependencia crítica del núcleo social.

## 10.1. Provider abstraction

Mantener:

```text
AIProvider
├── OpenAI-compatible
├── OpenRouter
├── Ollama
└── futuro proveedor
```

Separar:

- cliente;
- prompt;
- servicio;
- presupuesto;
- persistencia;
- observabilidad.

## 10.2. Input validation

Aceptar únicamente:

```text
user
assistant
```

si el endpoint no necesita `system`.

Nunca permitir al cliente controlar directamente:

```text
system prompt
tools
provider
model
temperature
max_tokens
```

salvo que exista una API administrativa explícita.

## 10.3. Límites

Definir:

- máximo de mensajes;
- máximo de caracteres por mensaje;
- máximo de contexto;
- máximo de tokens;
- timeout;
- retries;
- backoff.

## 10.4. Rate limiting IA

Crear throttle separado:

```text
AI requests/minute
AI requests/hour
AI requests/day
```

según producto y coste.

## 10.5. Presupuesto

Registrar:

- usuario;
- proveedor;
- modelo;
- tokens;
- coste estimado;
- duración;
- error;
- request ID.

## 10.6. Prompt injection

Aplicar:

- separación entre instrucciones del sistema y contenido del usuario;
- validación de herramientas;
- allowlist de herramientas;
- no ejecutar instrucciones recibidas desde libros/documentos como comandos;
- sanitización de contenido externo;
- límites de permisos.

## 10.7. Herramientas externas

Cada herramienta debe tener:

```text
name
schema
authorization
timeout
rate limit
audit
```

No permitir herramientas arbitrarias.

---

# 11. FASE 6 — Búsqueda [COMPLETADA]

**Prioridad: P1**

## 11.1. Búsqueda textual

Mantener PostgreSQL + `pg_trgm`.

Revisar índices:

- title;
- author;
- description;
- categories;
- normalized fields.

## 11.2. Ranking

Definir orden:

```text
exact match
prefix match
trigram similarity
popularity
rating
relevance
```

No utilizar popularidad para ocultar completamente resultados relevantes.

## 11.3. Paginación

Usar paginación estable.

Para grandes volúmenes, estudiar keyset pagination.

## 11.4. Semantic search

No llamar "semantic search" a un endpoint que solo utiliza `icontains`.

Implementación objetivo:

```text
query
 ↓
embedding
 ↓
pgvector
 ↓
candidate retrieval
 ↓
hybrid ranking
```

## 11.5. Embeddings

Definir:

- modelo;
- dimensión;
- versión;
- idioma;
- fecha;
- contenido fuente;
- estado.

Por ejemplo:

```text
embedding_model
embedding_version
embedded_at
embedding_status
```

## 11.6. Re-embedding

Debe existir estrategia cuando cambie:

- modelo;
- contenido;
- dimensión;
- algoritmo.

---

# 12. FASE 7 — Motor de recomendaciones [COMPLETADA]

**Prioridad: P1**

## 12.1. Mantener arquitectura por capas

```text
Candidate generation
        ↓
Feature extraction
        ↓
Scoring
        ↓
Filtering
        ↓
Diversity
        ↓
Explanation
        ↓
Top N
```

## 12.2. Candidate generation

Fuentes:

- géneros;
- autores;
- libros similares;
- usuarios similares;
- popularidad;
- tendencias;
- listas;
- contenido semánticamente similar.

## 12.3. Privacy filtering

Debe ejecutarse **antes de mostrar resultados**.

## 12.4. Feedback

Mantener eventos:

```text
shown
clicked
opened
wishlist
started
finished
rated
dismissed
```

## 12.5. Métricas

Medir:

```text
CTR
open rate
wishlist rate
start rate
completion rate
rating rate
dismiss rate
```

## 12.6. Versionado

Cada recomendación debe registrar:

```text
algorithm_version
strategy
metadata
```

## 12.7. No sobreoptimizar todavía

No crear un sistema ML complejo hasta disponer de datos suficientes.

Primero:

```text
rules
→ hybrid
→ semantic
→ learning-to-rank
```

solo cuando los datos lo justifiquen.

---

# 13. FASE 8 — Caché [COMPLETADA]

**Prioridad: P1**

## 13.1. Inventario de cachés

Documentar:

```text
book:{id}
user:{id}
recommendations:{user_id}
feed:{user_id}
search:{query}
```

## 13.2. TTL

Definir TTL por tipo:
- `TTL_BOOK_DETAIL = 900` (15 min)
- `TTL_USER_PROFILE = 900` (15 min)
- `TTL_RECOMMENDATIONS = 900` (15 min)
- `TTL_FEED = 300` (5 min)
- `TTL_SEARCH = 300` (5 min)
- `TTL_TRENDING = 900` (15 min)
- `TTL_STATS = 900` (15 min)

## 13.3. Invalidación

Documentar eventos:

```text
Review created
Review updated
Follow created
Follow deleted
User privacy changed
Book updated
Reading status changed
```

## 13.4. Stampede protection

Para operaciones costosas:

- locks;
- single-flight;
- stale-while-revalidate.
Implementado mediante `get_or_set_stampede_protected` con atomic lock `lock:{key}` en `books.cache_utils`.

## 13.5. Redis failure

La aplicación debe seguir funcionando de forma degradada cuando Redis no esté disponible, excepto las funcionalidades que dependan necesariamente de Redis.
Implementado mediante wrappers defensivos `safe_cache_get`, `safe_cache_set`, `safe_cache_delete` y `ResilientThrottleMixin` (`mybookconnect.throttling`), evitando errores 500 ante caídas de Redis.

### Entregable
`docs/architecture/caching.md` [COMPLETADO]

### Criterio de salida
- [x] Inventario exhaustivo de cachés y namespaces implementado en `books/cache_utils.py`.
- [x] Jerarquía de TTLs estándar definida centralizadamente.
- [x] Matriz de invalidaciones reactivas en cascada conectada a los 5 eventos clave del ciclo de vida.
- [x] Stampede protection con candado distribuido implementado en `get_or_set_stampede_protected`.
- [x] Resiliencia y degradación elegante ante caídas de Redis en capas de caché y throttling sin generar HTTP 500.
- [x] Documentación exhaustiva en `docs/architecture/caching.md`.
- [x] Cobertura de pruebas completa en `tests/test_phase08_caching.py` (10/10 passed).

---

# 14. FASE 9 — Performance y base de datos [COMPLETADA]

**Prioridad: P1**

## 14.1. N+1

Auditar:

- feed;
- books;
- reviews;
- profiles;
- followers;
- recommendations;
- lists;
- messages.

Erradicado N+1 mediante agregaciones anotadas en `UserProfileView`, precargas ordenadas con `Prefetch` en `ConversationViewSet`, `filter().exists()` directo en `CheckFollowStatusView` y optimizaciones en serializadores.

## 14.2. Índices

Revisar con:

```sql
EXPLAIN ANALYZE
```

No crear índices únicamente por intuición.
Verificado mediante `QueryProfiler.explain_analyze` asegurando tiempos de consulta crítica inferiores a 100 ms.

## 14.3. Índices prioritarios

Evaluar:

- foreign keys de alto uso;
- `(user, book)`;
- `(book, created_at)`;
- `(user, created_at)`;
- follows;
- messages;
- reviews;
- feedback;
- listas.

Implementados en migración `0024_book_idx_book_author_created_and_more`:
- `idx_book_author_created` en `Book(author, -created_at)`
- `idx_review_book_rating` en `Review(book, rating)`
- `idx_review_user_book` en `Review(user, book)`
- `idx_userbook_book_status` en `UserBook(book, status)`

## 14.4. Paginación

Todo endpoint potencialmente grande debe paginar.

No devolver:

```text
todos los seguidores
todos los libros
todos los mensajes
todos los comentarios
```

Garantizada paginación con `StandardResultsSetPagination` en seguidores, seguidos, libros y comentarios de reseñas (con límite de seguridad), y `StandardCursorPagination` en mensajes de chat.

## 14.5. Performance budgets

Definir objetivos iniciales:

```text
API p95 < 500 ms
API p99 < 1.5 s
queries críticas < 100 ms
```

Integrado en `ObservabilityMetricsService` con cálculo de percentiles `p95` y `p99`, y evaluación automática del estado `within_budget` / `breached`.

### Entregable
`docs/architecture/database_performance.md` [COMPLETADO]

### Criterio de salida
- [x] Auditoría N+1 resuelta en perfiles, mensajes, seguimiento y comentarios.
- [x] Nuevos índices compuestos creados y aplicados en PostgreSQL mediante migración `books.0024`.
- [x] Verificación de planes de ejecución eficientes mediante `QueryProfiler.explain_analyze`.
- [x] Paginación uniforme y acotación segura en endpoints de colecciones masivas.
- [x] Presupuestos de rendimiento (SLA p95 < 500ms, p99 < 1.5s, queries < 100ms) integrados en métricas de observabilidad.
- [x] Documentación exhaustiva en `docs/architecture/database_performance.md`.
- [x] Suite de pruebas automatizadas en `tests/test_phase09_performance.py` (9/9 passed).

---

# 15. FASE 10 — Frontend quality [COMPLETADA]

**Prioridad: P1**

## 10.1. Scripts

Asegurados y estandarizados en `frontend/package.json`:

```json
{
  "dev": "vite",
  "build": "tsc && vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "test:ui": "vitest --ui",
  "test:coverage": "vitest run --coverage",
  "test:e2e": "playwright test",
  "typecheck": "tsc --noEmit",
  "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 250",
  "lint:fix": "eslint . --ext ts,tsx --fix",
  "format": "prettier --write \"src/**/*.{ts,tsx,css,json}\"",
  "format:check": "prettier --check \"src/**/*.{ts,tsx,css,json}\""
}
```

## 10.2. ESLint

Configurado en `.eslintrc.cjs` con reglas estrictas y actualizadas para:
- React (`eslint-plugin-react`);
- hooks (`eslint-plugin-react-hooks`);
- TypeScript (`@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser`);
- accessibility (`eslint-plugin-jsx-a11y`).

## 10.3. Prettier

Unificado formato con `.prettierrc` y `.prettierignore`. Formateo ejecutado y validado mediante `pnpm format:check`.

## 10.4. Tests

Cobertura de pruebas unitarias y de componentes completa con Vitest + React Testing Library (10/10 suites, 27/27 tests pasando al 100%):
- autenticación (`Login.test.tsx`, `Register.test.tsx`);
- biblioteca (`Library.test.tsx`);
- reviews (`ReviewForm.test.tsx`);
- libros y detalle (`BookDetail.test.tsx`);
- listas de lectura (`ReadingLists.test.tsx`);
- perfiles y privacidad (`Profile.test.tsx`);
- interacciones sociales (`SocialInteractions.test.tsx`);
- navegación UX (`ScrollToTop.test.tsx`).

## 10.5. E2E

Configurado Playwright en `playwright.config.ts` y suite inicial de flujos críticos en `e2e/critical-flows.spec.ts`:
- Navegación catálogo y home;
- Formularios accesibles de autenticación (Login y Registro) con validaciones;
- Restauración de scroll al inicio ante cambios de ruta.

## 10.6. UX

- Implementado componente `ScrollToTop` en `frontend/src/components/layout/ScrollToTop.tsx` montado en `router.tsx` para restablecer `window.scrollTo({ top: 0, left: 0, behavior: 'instant' })` en cualquier cambio de ruta o navegación entre páginas.
- Gestión de estados de carga (`Spinner`), estados vacíos y accesibilidad con soporte para navegación fluida.

### Entregable
`docs/frontend/quality_and_testing.md` [COMPLETADO]

### Criterio de salida
- [x] Scripts estandarizados en `package.json` (`dev`, `build`, `preview`, `test`, `typecheck`, `lint`, `format`, `test:e2e`).
- [x] Linter ESLint configurado y pasando con 0 errores (`pnpm lint`).
- [x] Formateador Prettier configurado y verificado (`pnpm format:check`).
- [x] Typecheck de TypeScript pasando sin errores (`pnpm typecheck`).
- [x] Suite de pruebas Vitest ampliada y pasando al 100% (27/27 tests pasados).
- [x] Configuración y especificaciones de pruebas E2E con Playwright (`playwright.config.ts`, `e2e/critical-flows.spec.ts`).
- [x] Componente `ScrollToTop` activo y validado mediante pruebas unitarias para eliminar la persistencia indeseada del scroll entre vistas.
- [x] Documentación exhaustiva en `docs/frontend/quality_and_testing.md`.

---

# 16. FASE 11 — Backend testing [COMPLETADA]

**Prioridad: P1**

## 11.1. Unit

Servicios puros sin acoplamiento a base de datos:
- `normalize_isbn`: normalización de códigos ISBN-10 y 13.
- `_clean_goodreads_value`: limpieza de fórmulas Excel/Goodreads.
- `_parse_date`: parseo multiformato de fechas.
- `_map_goodreads_status`: mapeo semántico de estados de lectura.
- `CSVFormatDetector`: detección automática de dialectos CSV.

## 11.2. Integration

Django + PostgreSQL + Redis:
- Aislamiento transaccional y rollback atómico ante fallos en PostgreSQL.
- Almacenamiento seguro, lectura defensiva e invalidación reactiva en Redis (`safe_cache_set`, `safe_cache_get`, `safe_cache_delete`).

## 11.3. API

Endpoints críticos validados:
- Perfil autenticado (`/api/v1/auth/profile/`).
- Biblioteca personal y estados de lectura (`/api/v1/books/user/books/`).
- Estadísticas agregadas (`/api/v1/books/statistics/`).
- Previsualización y confirmación de importación masiva (`/api/v1/books/import/csv/preview/` y `confirm/`).

## 11.4. Security tests

Suite de seguridad:
- IDOR: un usuario no puede modificar ni borrar registros de biblioteca o reviews de otro usuario.
- Permisos y privacidad: restricción de acceso a perfiles privados y amigos mutuos.
- Bloqueos: usuarios bloqueados no pueden consultar el perfil del bloqueador.
- JWT: rechazo inmediato de peticiones no autenticadas (401).
- Rate limit: control de flujo y degradación elegante.
- Prompt injection: detección de patrones de jailbreak (`detect_prompt_injection`) y neutralización de tokens especiales (`sanitize_untrusted_input`).

## 11.5. Regression suite

- Resolución y blindaje de importaciones de Goodreads CSV con compatibilidad bidireccional de payloads (`raw_items_payload`, `valid_rows`).
- Resolución y blindaje del registro de lectura diaria y retos de objetivos anuales (`useAuthStore().token`).
- Suite de pruebas de regresión histórica permanente (79 tests pasando al 100%).

### Entregable
`docs/backend/testing_strategy.md` [COMPLETADO]

### Criterio de salida
- [x] Pruebas unitarias de servicios puros implementadas y pasando al 100%.
- [x] Pruebas de integración Django + PostgreSQL + Redis verificadas.
- [x] Pruebas de API sobre todos los endpoints centrales implementadas.
- [x] Suite de seguridad completa (IDOR, permisos, bloqueos, auth, prompt injection).
- [x] Suite de regresión histórica automatizada (`test_phase11_backend_testing.py`).
- [x] Documentación exhaustiva en `docs/backend/testing_strategy.md`.

---

# 17. FASE 12 — CI/CD [COMPLETADA]

**Prioridad: P0/P1**

El objetivo es impedir que una regresión llegue a `develop`.

## Pipeline

```text
push / PR
   ↓
backend lint (Ruff)
   ↓
backend tests (Pytest + PostgreSQL real + Redis real)
   ↓
migration check (makemigrations --check --dry-run)
   ↓
frontend lint (ESLint)
   ↓
frontend format check (Prettier)
   ↓
frontend typecheck (TypeScript tsc --noEmit)
   ↓
frontend tests (Vitest)
   ↓
frontend build (Vite)
   ↓
Docker build (Backend + Frontend)
   ↓
security checks (Bandit SAST + pip-audit + pnpm audit)
   ↓
PR status
```

## 17.1. GitHub Actions

Implementados workflows modulares:
- `.github/workflows/ci-backend.yml`: Linting con Ruff, verificación de migraciones y pruebas automatizadas sobre servicios en contenedor de PostgreSQL 16 (`pgvector`) y Redis 7 reales.
- `.github/workflows/ci-frontend.yml`: Verificación de formato Prettier, análisis ESLint, chequeo estricto de tipos con TypeScript, suite de pruebas unitarias/componentes con Vitest y compilación de producción de Vite.
- `.github/workflows/ci-docker.yml`: Construcción y verificación de imágenes Docker de backend y frontend multi-stage.
- `.github/workflows/security.yml`: Análisis estático de código Python (Bandit SAST) y auditorías de vulnerabilidades en dependencias (`pip-audit` y `pnpm audit`).

## 17.2. PostgreSQL real

Los tests de backend se ejecutan contra PostgreSQL 16 real (`pgvector/pgvector:pg16`) con healthchecks automáticos en el servicio de CI.

## 17.3. Redis real

Las pruebas de caché, Channels y Celery se ejecutan contra Redis 7 real (`redis:7-alpine`) en el pipeline de GitHub Actions.

## 17.4. Dependency updates

Configurado `.github/dependabot.yml` con escaneos programados para `pip`, `npm/pnpm` y `github-actions`.

### Entregable
`docs/devops/ci_cd_pipeline.md` [COMPLETADO]

### Criterio de salida
- [x] Pipelines de CI para Backend y Frontend configurados y probados.
- [x] Servicio PostgreSQL 16 (`pgvector`) y Redis 7 reales integrados en el runner.
- [x] Verificación de migraciones y linters estáticos en cada PR.
- [x] Pipeline de validación de compilación de imágenes Docker implementado.
- [x] Escaneo de seguridad (Bandit SAST, pip-audit, pnpm audit) activo.
- [x] Dependabot configurado para actualización automática de dependencias.
- [x] Documentación exhaustiva en `docs/devops/ci_cd_pipeline.md`.

---

# 18. FASE 13 — Docker y producción [COMPLETADA]

**Prioridad: P1**

## 18.1. Separación

Producción estructurada con aislamiento estricto por capas de red:

```text
Internet
   ↓ (80/443)
Reverse proxy (Nginx:1.27-alpine en 'frontend_net')
   ↓ (8000 interno)
Backend ASGI (Daphne en 'frontend_net' + 'backend_net')
   ↓ (red interna 'backend_net' internal: true)
PostgreSQL 16 (pgvector)
Redis 7 (Alpine)
Celery (Worker asíncrono)
```

- Bases de datos (PostgreSQL 16) y caché/broker (Redis 7) aisladas en `backend_net` privada sin puertos publicados al host (`ports` omitido).
- Frontend Nginx aislado sin pertenencia a `backend_net`.

## 18.2. Backend

Django/Daphne no expone ningún puerto hacia el host exterior (`ports` eliminado, únicamente `expose: ["8000"]`). Todo el tráfico web y WebSocket es mediado y saneado por el reverse proxy Nginx.

## 18.3. Healthchecks

Implementadas y verificadas las sondas canónicas desacopladas:

```text
/health/live   -> Sonda de Liveness (proceso ASGI vivo, sin dependencias)
/health/ready  -> Sonda de Readiness (conectividad con PostgreSQL y Redis)
```

### Liveness
- Comprueba que el proceso de la aplicación está activo y responde peticiones HTTP sin interrupciones. Resiliente a indisponibilidad temporal de DB o caché para evitar ciclos de reinicio (*crash loops*).

### Readiness
- Comprueba conectividad real mediante `SELECT 1;` en PostgreSQL y set/get en Redis. Si alguna dependencia crítica falla, retorna `503 SERVICE UNAVAILABLE`.

## 18.4. Graceful shutdown

Configurado el manejo de señales de apagado y periodos de gracia en `docker-compose.prod.yml`:
- **Nginx (`frontend`):** `stop_signal: SIGQUIT`, `stop_grace_period: 10s`.
- **Daphne (`backend`):** `stop_signal: SIGTERM`, `stop_grace_period: 30s` (drena conexiones HTTP y WS activas).
- **Celery (`celery_worker`):** `stop_signal: SIGTERM`, `stop_grace_period: 60s` (warm shutdown de tareas asíncronas en ejecución).

## 18.5. Volúmenes

Persistencia desacoplada del ciclo de vida de los contenedores mediante volúmenes nombrados:
- `db_prod_data` (`/var/lib/postgresql/data`): Persistencia de esquemas y datos de PostgreSQL 16.
- `backend_media` (`/app/media`): Archivos subidos por usuarios; montado en Nginx en modo solo lectura (`ro`).
- `backend_static` (`/app/staticfiles`): Archivos estáticos de Django con caché inmutable; montado en Nginx en modo solo lectura (`ro`).
- `backups_data` (`/app/backups`): Directorio persistente de copias de seguridad de bases de datos.

### Entregables
- `docker-compose.prod.yml` [COMPLETADO]
- `frontend/nginx.conf` [COMPLETADO]
- `backend/mybookconnect/urls.py` [COMPLETADO]
- `backend/tests/test_phase13_docker_production.py` [COMPLETADO]
- `docs/devops/production_docker.md` [COMPLETADO]

### Criterio de salida
- [x] Aislamiento de redes de producción verificado (`frontend_net` y `backend_net internal: true`).
- [x] PostgreSQL, Redis y Django sin puertos expuestos al host en producción.
- [x] Sondas canónicas `/health/live` y `/health/ready` implementadas y verificadas con suite de tests dedicada.
- [x] Graceful shutdown implementado con señales y tiempos de gracia en Daphne, Celery y Nginx.
- [x] Volúmenes persistentes nombrados y documentados.
- [x] Suite de pruebas automatizadas de Fase 13 pasando al 100%.

---

# 19. FASE 14 — Observabilidad [COMPLETADA]

**Prioridad: P1**

## 19.1. Logs

Implementado formateador JSON con los 7 campos canónicos obligatorios:

```text
timestamp
request_id
user_id
method
path
status
duration
```

Sanitización estricta (`sanitize_sensitive_data`):
- Ningún password (`password`, `confirm_password`, `pwd`).
- Ningún JWT (tokens JWT directos o con esquema `Bearer ***REDACTED***`).
- Ninguna API key ni secreto de autenticación.
- Ningún dato privado sensible.

## 19.2. Métricas

Implementados servicios de cálculo y agregación en tiempo real:

### Backend (`ObservabilityMetricsService`):
- `requests`: total, rate 4xx y rate 5xx.
- `latency`: promedio y percentiles `p50`, `p95`, `p99`.
- `5xx` y `4xx`: conteos acumulados y ratios porcentuales.
- `DB latency`: tiempo de respuesta de PostgreSQL medido en milisegundos (`measure_db_latency`).
- `Redis latency`: tiempo de round-trip de Redis medido en milisegundos (`measure_redis_latency`).
- `Celery queue`: profundidad de la cola de tareas (`get_celery_queue_depth`).
- `Celery failures`: total de fallos de tareas en segundo plano.
- `WebSocket connections`: conexiones activas concurrentes a Channels/Daphne.

### Producto (`ProductMetricsService`):
- `DAU`: usuarios activos en 24h.
- `WAU`: usuarios activos en 7 días.
- `MAU`: usuarios activos en 30 días.
- `retention`: ratio porcentual de retención (`wau / mau * 100`).
- `books added`: total libros en estanterías de usuarios (`UserBook`).
- `reviews`: total reseñas publicadas no eliminadas (`Review`).
- `follows`: total conexiones sociales activas.
- `messages`: total mensajes enviados en el sistema de chat.
- `recommendation interactions`: total valoraciones y feedback sobre recomendaciones.

## 19.3. Alertas

Implementado motor de evaluación en tiempo real (`SystemAlertsEvaluator`) para:
- `5xx elevado`: alerta `CRITICAL` si ratio > 1.0% con peticiones mínimas.
- `DB unavailable`: alerta `CRITICAL` si PostgreSQL no responde al ping.
- `Redis unavailable`: alerta `CRITICAL` si Redis no responde al ping.
- `Celery backlog`: alerta `WARNING` si la cola de tareas supera 100 elementos.
- `disk usage`: alerta `WARNING` si el uso de disco supera el 85%.
- `memory`: monitoreo de saturación de memoria RAM.
- `error rate`: alerta `WARNING` si el ratio combinado 4xx+5xx supera el 5.0%.

### Entregables
- `backend/mybookconnect/logging_formatters.py` [COMPLETADO]
- `backend/mybookconnect/observability.py` [COMPLETADO]
- `backend/tests/test_phase14_observability.py` [COMPLETADO]
- `docs/devops/observability_and_metrics.md` [COMPLETADO]

### Criterio de salida
- [x] Formato JSON estructurado con los 7 campos canónicos obligatorios en cada log.
- [x] Sanitización estricta de contraseñas, tokens JWT, Bearer tokens y API keys verificada con pruebas.
- [x] Métricas de backend completas (latencias p50/p95/p99, DB latency, Redis latency, Celery queue depth, WS).
- [x] Métricas de producto implementadas y cacheadas (DAU, WAU, MAU, retención, libros, reseñas, chat).
- [x] Motor de alertas de salud operativa implementado con los 7 criterios del Roadmap.
- [x] Endpoint administrativo seguro `/api/v1/observability/metrics/` con control de acceso `IsAdminUser`.
- [x] Suite de pruebas automatizadas de Fase 14 pasando al 100% (14/14 tests).
- [x] Documentación técnica en `docs/devops/observability_and_metrics.md`.

---

# 20. FASE 15 — Backups y disaster recovery

**Prioridad: P0 para producción**

## 20.1. PostgreSQL

Definir:

- frecuencia;
- retención;
- cifrado;
- almacenamiento externo.

## 20.2. Media

Backups independientes.

## 20.3. Redis

No tratar Redis como fuente de verdad.

## 20.4. Restore test

Un backup que nunca se restaura no está validado.

Crear procedimiento:

```text
backup
→ restore
→ migrate/check
→ smoke tests
```

## 20.5. RPO/RTO

Definir objetivos antes de producción.

Inicialmente:

```text
RPO: 24 h
RTO: 4 h
```

y reducirlos si el producto lo requiere.

---

# 21. FASE 16 — Moderación y seguridad social

**Prioridad: P1 antes de beta abierta**

## 21.1. Reportes

Permitir reportar:

- usuario;
- review;
- comentario;
- lista;
- mensaje si procede.

## 21.2. Moderación

Modelo:

```text
Report
├── reporter
├── target
├── reason
├── description
├── status
├── moderator
├── resolution
└── timestamps
```

## 21.3. Estados

```text
open
investigating
resolved
dismissed
```

## 21.4. Rate limits

Evitar abuso de:

- reports;
- follows;
- comments;
- likes;
- messages.

## 21.5. Contenido

Definir política de:

- spam;
- acoso;
- contenido ilegal;
- suplantación;
- copyright;
- spoilers.

---

# 22. FASE 17 — Cuenta y privacidad del usuario

**Prioridad: P1**

Implementar/revisar:

- cambio de email;
- verificación email;
- password reset;
- cambio de password;
- sesiones;
- logout global;
- exportación de datos;
- eliminación de cuenta;
- anonimización;
- consentimiento cuando proceda.

## 22.1. Eliminación

Definir qué ocurre con:

- reviews;
- comentarios;
- follows;
- listas;
- mensajes;
- actividad;
- feedback;
- recomendaciones.

## 22.2. Export

Formato inicial:

```text
JSON
```

con:

- perfil;
- biblioteca;
- reviews;
- listas;
- follows si legalmente corresponde;
- preferencias.

---

# 23. FASE 18 — Legal y privacidad para beta

**Prioridad: P1 antes de usuarios reales**

Preparar:

- aviso legal;
- política de privacidad;
- política de cookies si se utilizan;
- términos de uso;
- política de contenido;
- política de eliminación;
- contacto.

Documentar:

- datos recogidos;
- finalidad;
- proveedores;
- IA;
- analytics;
- cookies;
- retención.

No introducir tracking innecesario.

---

# 24. FASE 19 — Producto: onboarding

**Prioridad: P1**

Objetivo:

> conseguir que un usuario nuevo entienda el producto en pocos minutos.

## Flujo

```text
registro
 ↓
perfil básico
 ↓
géneros/intereses
 ↓
seleccionar libros conocidos
 ↓
valoraciones opcionales
 ↓
primeras recomendaciones
 ↓
seguir usuarios
 ↓
feed
```

## Métrica

Definir:

```text
activation rate
```

Ejemplo:

> usuario que completa perfil + añade X libros + interactúa con una recomendación.

---

# 25. FASE 20 — Descubrimiento de libros

**Prioridad: P1/P2**

Construir progresivamente:

- tendencias;
- populares;
- novedades;
- por género;
- por autor;
- similares;
- recomendaciones personales;
- listas de usuarios;
- descubrimiento social.

Evitar que todo dependa de IA.

---

# 26. FASE 21 — Listas sociales

**Prioridad: P1/P2**

Evolucionar listas hacia:

```text
public
followers
private
```

Funciones:

- crear;
- editar;
- ordenar;
- seguir;
- compartir;
- comentar;
- guardar;
- duplicar opcionalmente.

## Métricas

- listas creadas;
- libros/lista;
- seguidores/lista;
- aperturas.

---

# 27. FASE 22 — Feed

**Prioridad: P1/P2**

Eventos potenciales:

```text
started reading
finished reading
reviewed
created list
followed
liked
commented
```

## Ranking

Primera versión:

```text
recencia
+
relación social
+
tipo de evento
```

No crear ML para feed antes de tener suficiente tráfico.

## Controles

Permitir:

- silenciar;
- dejar de seguir;
- bloquear;
- ocultar contenido.

---

# 28. FASE 23 — Notificaciones

**Prioridad: P1/P2**

Eventos:

- follow;
- follow accepted;
- review like;
- comment;
- reply;
- list follow;
- message;
- recommendation.

Canales:

```text
in-app
email opcional
push futuro
```

## Preferencias

Por usuario y tipo.

---

# 29. FASE 24 — IA de producto

**Prioridad: P2**

Solo después de tener IA segura.

Posibilidades:

### Asistente literario

- explicar libros;
- comparar temas;
- recomendar;
- generar resúmenes;
- ayudar a descubrir.

### Resúmenes

Siempre etiquetados como generados por IA.

### Recomendaciones

Usar IA como señal, no como autoridad absoluta.

### Moderación asistida

IA como apoyo a moderadores, no como única decisión para casos importantes.

---

# 30. FASE 25 — Embeddings y pgvector

**Prioridad: P2**

Introducir cuando la búsqueda textual y el sistema híbrido lo justifiquen.

## Arquitectura

```text
Book
 ↓
content normalization
 ↓
embedding job
 ↓
pgvector
 ↓
ANN search
 ↓
hybrid ranking
```

## Versionado

No mezclar embeddings de modelos incompatibles.

---

# 31. FASE 26 — Analytics de producto

**Prioridad: P1/P2**

Definir eventos:

```text
signup
login
book_view
book_added
reading_started
reading_finished
review_created
follow_created
list_created
recommendation_shown
recommendation_clicked
recommendation_dismissed
message_sent
```

## Embudo

```text
visit
 ↓
signup
 ↓
activation
 ↓
retention
 ↓
social interaction
 ↓
reading activity
```

---

# 32. FASE 27 — Beta cerrada

**Prioridad: P0 de lanzamiento**

No lanzar a todo el mundo inmediatamente.

## Grupo inicial

Objetivo inicial:

```text
10–30 usuarios
```

Después:

```text
50–100
```

## Checklist

- [ ] registro;
- [ ] login;
- [ ] recuperación;
- [ ] biblioteca;
- [ ] búsqueda;
- [ ] reviews;
- [ ] follows;
- [ ] privacidad;
- [ ] bloqueos;
- [ ] feed;
- [ ] listas;
- [ ] recomendaciones;
- [ ] chat si está habilitado;
- [ ] reporting;
- [ ] eliminación de cuenta;
- [ ] backups;
- [ ] monitoring.

## Feedback

Crear formulario interno con:

```text
bug
confusing UX
missing feature
performance
privacy concern
recommendation quality
general feedback
```

---

# 33. FASE 28 — Beta abierta

Condiciones:

- P0 = 0;
- vulnerabilidades críticas = 0;
- privacidad auditada;
- backups probados;
- CI estable;
- monitoring activo;
- error rate conocido;
- costes conocidos.

---

# 34. FASE 29 — Preparación de producción

## Infraestructura

- [ ] dominio;
- [ ] HTTPS;
- [ ] DNS;
- [ ] reverse proxy;
- [ ] PostgreSQL gestionado;
- [ ] Redis;
- [ ] worker;
- [ ] backups;
- [ ] almacenamiento media;
- [ ] logs;
- [ ] monitoring.

## Seguridad

- [ ] secretos fuera de repo;
- [ ] production DEBUG=False;
- [ ] ALLOWED_HOSTS correcto;
- [ ] CORS correcto;
- [ ] CSRF correcto;
- [ ] cookies;
- [ ] CSP;
- [ ] rate limiting;
- [ ] JWT;
- [ ] uploads.

---

# 35. FASE 30 — Escalabilidad

Solo cuando los datos reales indiquen necesidad.

## Etapa 1

Un backend + worker + DB + Redis.

## Etapa 2

Escalar backend horizontalmente.

## Etapa 3

Separar workers:

```text
default
books
AI
recommendations
emails
```

## Etapa 4

Optimizar:

- DB;
- Redis;
- CDN;
- object storage;
- pgvector.

No introducir microservicios prematuramente.

---

# 36. FASE 31 — Monetización

No priorizar hasta validar retención.

Posibles líneas:

## Afiliación

- libros;
- ebooks;
- audiolibros.

## Premium

Posibles funciones:

- estadísticas avanzadas;
- recomendaciones avanzadas;
- personalización;
- IA;
- listas avanzadas.

## Autores/editoriales

- perfiles;
- herramientas;
- campañas;
- contenido patrocinado claramente identificado.

## Publicidad

Solo si:

- no perjudica UX;
- no manipula recomendaciones;
- está claramente identificada.

---

# 37. FASE 32 — Escalabilidad de recomendaciones

Cuando exista suficiente feedback:

```text
rules
 ↓
hybrid
 ↓
collaborative filtering
 ↓
semantic
 ↓
learning-to-rank
```

Variables:

- historial;
- ratings;
- géneros;
- autores;
- similitud;
- contexto;
- feedback.

Evitar usar atributos sensibles.

---

# 38. FASE 33 — Calidad avanzada

Introducir:

- contract tests;
- E2E;
- load tests;
- security tests;
- mutation testing si aporta valor;
- profiling;
- query benchmarks.

## Objetivos

Repetibilidad > cantidad de tests.

---

# 39. FASE 34 — Release engineering

Definir:

```text
MAJOR
MINOR
PATCH
```

y changelog.

Cada release debe incluir:

- features;
- fixes;
- security;
- migrations;
- breaking changes.

---

# 40. FASE 35 — Limpieza técnica continua

Cada sprint:

- eliminar código muerto;
- eliminar endpoints legacy;
- revisar TODOs;
- actualizar dependencias;
- revisar logs;
- revisar índices;
- revisar documentación;
- revisar ADRs.

---

# 41. Backlog técnico consolidado

## P0 — Antes de beta

- [ ] PrivacyService.
- [ ] Auditoría feed.
- [ ] Auditoría ReadingMatch.
- [ ] Auditoría usuarios similares.
- [ ] Auditoría recomendaciones.
- [ ] Auditoría listas.
- [ ] Bloqueo bidireccional.
- [ ] Rating 1–5.
- [ ] Fuente única Review.rating.
- [ ] Tests de privacidad.
- [ ] IDOR audit.
- [ ] health/live.
- [ ] health/ready.
- [ ] CI backend.
- [ ] CI frontend.
- [ ] CI migrations.
- [ ] Docker build.
- [ ] backup/restore test.
- [ ] producción DEBUG=False.

## P1 — Antes de beta abierta

- [ ] WebSocket auth segura.
- [ ] Chat read state.
- [ ] AI validation.
- [ ] AI throttling.
- [ ] AI budget.
- [ ] upload hardening.
- [ ] E2E.
- [ ] observabilidad.
- [ ] alertas.
- [ ] reportes.
- [ ] account deletion.
- [ ] export.
- [ ] email verification.
- [ ] password reset.
- [ ] documentación consolidada.

## P2 — Evolución

- [ ] pgvector.
- [ ] semantic search real.
- [ ] recommendation ranking avanzado.
- [ ] AI assistant ampliado.
- [ ] analytics avanzado.
- [ ] push notifications.
- [ ] gamificación.
- [ ] premium.
- [ ] author tools.

---

# 42. Matriz de prioridad

| Área | Prioridad | Bloquea beta |
|---|---|---|
| Privacidad | P0 | Sí |
| Integridad datos | P0 | Sí |
| Autorización | P0 | Sí |
| IDOR | P0 | Sí |
| Backups | P0 | Sí |
| CI | P0 | Sí |
| WebSockets | P1 | Si chat activo |
| IA | P1 | No, salvo que sea core |
| Búsqueda | P1 | No |
| Recomendaciones | P1 | No |
| Frontend tests | P1 | Sí para beta |
| Observabilidad | P1 | Sí |
| Moderación | P1 | Sí para beta abierta |
| pgvector | P2 | No |
| ML | P2 | No |
| Premium | P2 | No |
| Gamificación | P2 | No |

---

# 43. Orden exacto recomendado

La secuencia recomendada es:

```text
FASE 0
Baseline
   ↓
FASE 1
Dominio + integridad
   ↓
FASE 2
Privacy Core
   ↓
FASE 3
Seguridad
   ↓
FASE 4
WebSockets
   ↓
FASE 5
IA segura
   ↓
FASE 6
Búsqueda
   ↓
FASE 7
Recomendaciones
   ↓
FASE 8
Caché
   ↓
FASE 9
Performance
   ↓
FASE 10
Frontend quality
   ↓
FASE 11
Backend testing
   ↓
FASE 12
CI/CD
   ↓
FASE 13
Docker production
   ↓
FASE 14
Observabilidad
   ↓
FASE 15
Backups
   ↓
FASE 16
Moderación
   ↓
FASE 17
Cuenta / privacidad
   ↓
FASE 18
Legal
   ↓
FASE 19
Onboarding
   ↓
FASE 20–26
Producto
   ↓
FASE 27
Beta cerrada
   ↓
FASE 28
Beta abierta
   ↓
FASE 29
Producción
   ↓
FASE 30+
Escalado
```

---

# 44. Criterios de salida de Beta Cerrada

La beta cerrada puede comenzar cuando:

## Seguridad

- [ ] No hay vulnerabilidades P0/P1 conocidas.
- [ ] No existen endpoints sociales sin autorización.
- [ ] PrivacyService cubre superficies principales.
- [ ] IDOR auditado.
- [ ] JWT auditado.
- [ ] WebSocket auditado.
- [ ] uploads auditados.

## Datos

- [ ] rating único.
- [ ] constraints correctas.
- [ ] migraciones reproducibles.
- [ ] backups.
- [ ] restore probado.

## Calidad

- [ ] backend tests verdes.
- [ ] frontend tests verdes.
- [ ] typecheck verde.
- [ ] lint verde.
- [ ] build verde.
- [ ] Docker build verde.
- [ ] E2E de smoke verde.

## Operación

- [ ] logs.
- [ ] métricas.
- [ ] alertas.
- [ ] healthchecks.
- [ ] Celery monitorizado.
- [ ] DB monitorizada.
- [ ] Redis monitorizado.

## Producto

- [ ] onboarding básico.
- [ ] búsqueda.
- [ ] biblioteca.
- [ ] reviews.
- [ ] follows.
- [ ] feed.
- [ ] privacidad.
- [ ] bloqueo.
- [ ] recomendaciones básicas.
- [ ] listas.

---

# 45. Criterios de salida de Beta Abierta

- [ ] Retención inicial medida.
- [ ] Errores conocidos documentados.
- [ ] Soporte básico.
- [ ] Reporting.
- [ ] Moderación.
- [ ] Legal.
- [ ] Costes conocidos.
- [ ] Backups automatizados.
- [ ] Restore documentado.
- [ ] Alertas.
- [ ] CI/CD.
- [ ] Rollback probado.

---

# 46. Métricas de producto

No medir únicamente usuarios registrados.

## Adquisición

```text
visits
signups
signup conversion
```

## Activación

```text
profile completed
books added
first review
first follow
first recommendation click
```

## Engagement

```text
DAU
WAU
MAU
sessions/user
books/user
reviews/user
```

## Retención

```text
D1
D7
D30
```

## Social

```text
follows
comments
likes
messages
lists
```

## Discovery

```text
searches
book views
recommendation CTR
wishlist
reading starts
```

---

# 47. Principios de producto

## No competir por cantidad de funcionalidades

La ventaja debe estar en:

```text
descubrir
+
leer
+
compartir
+
conectar
```

## No convertir la IA en el producto

La IA debe mejorar:

- descubrimiento;
- comprensión;
- personalización.

No sustituir la experiencia social.

## No manipular recomendaciones por monetización

Si existe afiliación/publicidad:

```text
ranking orgánico
        +
publicidad claramente separada
```

No mezclar ambos silenciosamente.

---

# 48. ADRs recomendados

Mantener/actualizar:

```text
ADR-001 Django + React
ADR-002 PostgreSQL source of truth
ADR-003 Redis cache/realtime
ADR-004 Celery
ADR-005 JWT
ADR-006 UserBook vs Review
ADR-007 Hybrid Search
ADR-008 Recommendations
```

Añadir:

```text
ADR-009 Privacy Core
ADR-010 WebSocket Authentication
ADR-011 AI Provider Architecture
ADR-012 AI Cost Controls
ADR-013 Moderation
ADR-014 Account Deletion/Data Export
ADR-015 Backup/Recovery
ADR-016 Observability
ADR-017 Beta Deployment
ADR-018 pgvector
```

Cada ADR debe explicar:

- contexto;
- decisión;
- alternativas;
- consecuencias;
- fecha;
- estado.

---

# 49. Protocolo de trabajo para el agente

Antes de tocar código:

```text
1. Leer Roadmap.md
2. Leer instruccionesAgente.md
3. Inspeccionar código actual
4. Comprobar si el problema sigue existiendo
5. Localizar tests existentes
6. Diseñar cambio mínimo
7. Implementar
8. Añadir tests
9. Ejecutar validaciones
10. Revisar diff
11. Actualizar documentación
12. Commit
13. Push a develop
```

Nunca asumir que una tarea del roadmap sigue pendiente sin comprobar primero el código.

---

# 50. Ciclo obligatorio de cada tarea

```text
ANALYZE
   ↓
PLAN
   ↓
IMPLEMENT
   ↓
TEST
   ↓
FIX
   ↓
REVIEW
   ↓
DOCS
   ↓
COMMIT
   ↓
PUSH
```

Si una prueba falla:

```text
NO marcar fase como completada.
```

---

# 51. Reglas para cambios destructivos

Requieren confirmación antes de ejecutar:

- eliminar datos;
- eliminar columnas;
- borrar endpoints públicos;
- cambiar identificadores;
- migraciones destructivas;
- modificar autenticación;
- cambiar protocolo WebSocket;
- sustituir infraestructura;
- eliminar funcionalidad usada por beta.

Preferir:

```text
add
→ migrate
→ backfill
→ switch
→ verify
→ remove legacy
```

---

# 52. Plan inmediato recomendado

El siguiente sprint debe ser deliberadamente pequeño.

## Sprint 1 — Privacy & Integrity

### Tarea 1
Auditar todos los endpoints sociales.

### Tarea 2
Implementar `PrivacyService`.

### Tarea 3
Integrarlo en:

- feed;
- ReadingMatch;
- similar users;
- recommendations;
- lists.

### Tarea 4
Auditar bloqueos bidireccionales.

### Tarea 5
Unificar rating.

### Tarea 6
Añadir validadores 1–5.

### Tarea 7
Añadir tests de matriz de privacidad.

### Tarea 8
Documentar ADR-009.

### Tarea 9
Ejecutar suite completa.

### Tarea 10
Commit:

```text
security: harden social privacy and data integrity
```

---

# 53. Sprint 2 — Security & Realtime

- WebSocket auth.
- AI input validation.
- AI rate limit.
- upload hardening.
- IDOR audit.
- security tests.
- chat read state si procede.

---

# 54. Sprint 3 — Quality & CI

- frontend scripts;
- ESLint;
- Prettier;
- Vitest;
- Playwright;
- GitHub Actions;
- Docker tests;
- migration checks.

---

# 55. Sprint 4 — Production readiness

- health endpoints;
- observability;
- backups;
- restore;
- Docker production;
- reverse proxy;
- secrets;
- deployment checklist.

---

# 56. Sprint 5 — Beta

- onboarding;
- reporting;
- account management;
- legal;
- first testers;
- feedback loop;
- bug fixing.

---

# 57. Lo que NO se debe hacer todavía

Hasta superar Beta Cerrada:

- [ ] No crear microservicios.
- [ ] No introducir Kubernetes.
- [ ] No crear ML complejo.
- [ ] No añadir decenas de funcionalidades sociales.
- [ ] No optimizar prematuramente Redis.
- [ ] No cambiar de PostgreSQL.
- [ ] No añadir infraestructura distribuida sin necesidad.
- [ ] No depender obligatoriamente de un proveedor LLM.
- [ ] No introducir publicidad que altere recomendaciones.
- [ ] No almacenar secretos en frontend.
- [ ] No exponer endpoints internos.
- [ ] No permitir que el frontend determine permisos.

---

# 58. Visión a largo plazo

La arquitectura objetivo es:

```text
                         ┌─────────────────────┐
                         │       Cliente       │
                         │ React + TypeScript  │
                         └──────────┬──────────┘
                                    │
                              HTTPS / WS
                                    │
                         ┌──────────▼──────────┐
                         │ Reverse Proxy / CDN │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
          ┌─────────▼─────────┐           ┌────────▼────────┐
          │ Django / DRF      │           │ Channels/Daphne │
          │ REST API          │           │ WebSockets      │
          └─────────┬─────────┘           └────────┬────────┘
                    │                              │
                    └──────────────┬───────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             │                     │                     │
       ┌─────▼─────┐        ┌──────▼──────┐       ┌─────▼─────┐
       │ PostgreSQL│        │    Redis     │       │  Celery   │
       │ source of │        │ cache / WS / │       │ workers   │
       │ truth     │        │ rate limits  │       │           │
       └─────┬─────┘        └──────────────┘       └─────┬─────┘
             │                                             │
             │                                      ┌──────▼──────┐
             │                                      │ AI / Books  │
             │                                      │ Providers   │
             │                                      └─────────────┘
             │
       ┌─────▼─────────────────────────────────────────────┐
       │              Domain Services                      │
       │ Privacy / Books / Reviews / Feed / Recs / Lists  │
       └───────────────────────────────────────────────────┘
```

La característica más importante de esta arquitectura no es añadir componentes, sino mantener claras las responsabilidades.

---

# 59. Resultado final esperado

Al completar este roadmap, MyBookConnect deberá cumplir:

### Producto

- red social literaria funcional;
- biblioteca personal;
- reviews;
- perfiles;
- follows;
- feed;
- listas;
- recomendaciones;
- mensajería;
- búsqueda;
- IA opcional.

### Seguridad

- autenticación robusta;
- autorización;
- privacidad centralizada;
- bloqueo;
- rate limiting;
- protección de uploads;
- IA controlada;
- WebSocket seguro.

### Calidad

- tests backend;
- tests frontend;
- E2E;
- typecheck;
- lint;
- CI;
- Docker.

### Operación

- despliegue reproducible;
- healthchecks;
- logs;
- métricas;
- alertas;
- backups;
- restore.

### Escalabilidad

- PostgreSQL optimizado;
- Redis;
- Celery;
- búsqueda híbrida;
- pgvector cuando corresponda;
- recomendaciones versionadas.

### Producto real

- onboarding;
- métricas;
- feedback;
- beta;
- moderación;
- soporte;
- legal.

---

# 60. Regla final

**MyBookConnect no necesita más complejidad ahora mismo. Necesita consolidación.**

La prioridad de la siguiente etapa es:

```text
PRIVACIDAD
    ↓
INTEGRIDAD
    ↓
SEGURIDAD
    ↓
CALIDAD
    ↓
CI/CD
    ↓
OBSERVABILIDAD
    ↓
BETA
    ↓
DATOS REALES
    ↓
EVOLUCIÓN DEL PRODUCTO
```

La arquitectura actual ya permite continuar desarrollando sin rehacer el proyecto desde cero. El trabajo inmediato debe centrarse en cerrar las superficies de privacidad, eliminar ambigüedades de dominio, blindar IA/WebSockets, automatizar la calidad y preparar una beta controlada.

**No se considera que una fase esté completada por tener código implementado. Se considera completada cuando el comportamiento está probado, documentado, integrado y verificable.**
