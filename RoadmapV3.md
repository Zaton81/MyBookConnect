# MyBookConnect / My Book Social — Roadmap de Producción

> Roadmap para llevar MyBookConnect a una primera versión pública estable, segura, mantenible y preparada para producción.

## Principios

1. No añadir funcionalidades complejas mientras existan problemas de seguridad, integridad o infraestructura.
2. Priorizar libros, autores, lectores, biblioteca, reseñas, relaciones sociales y descubrimiento.
3. Toda funcionalidad nueva debe tener tests, respetar permisos y privacidad, reutilizar la arquitectura existente y documentarse cuando afecte a la arquitectura.
4. Las operaciones costosas deben ser asíncronas mediante Celery.
5. La IA debe ser opcional y nunca bloquear las funcionalidades principales.
6. No realizar migraciones destructivas sin estrategia de rollback.
7. Antes del lanzamiento debe existir un procedimiento probado de backup y restore.

---

# 1. 🔴 Seguridad e integridad — P0

## 1.1 Notificaciones

- [x] Eliminar el `POST` público de `/notifications/`.
- [x] Mantener únicamente lectura para el usuario autenticado.
- [x] Crear un servicio interno para generar notificaciones.
- [x] Impedir que un usuario genere notificaciones para terceros.
- [x] Añadir tests de autorización.
- [x] Revisar follows, likes, comentarios, mensajes, reseñas, sistema y administración.

## 1.2 Observabilidad

- [x] Auditar `/api/v1/observability/metrics/`.
- [x] Confirmar que solo usuarios autorizados pueden acceder.
- [x] No exponer métricas, infraestructura, credenciales ni información de otros usuarios.
- [x] Añadir tests de permisos.

## 1.3 WebSockets

### Autenticación

- [x] Eliminar progresivamente `?token=...`.
- [x] Priorizar cookie HttpOnly/Secure o ticket efímero.
- [x] Impedir que JWT aparezca en logs, URLs, monitorización, historial o proxies.

### Robustez

- [x] Capturar `JSONDecodeError`.
- [x] Rechazar payloads malformados.
- [x] Establecer tamaño máximo de mensaje.
- [x] Validar cada acción.
- [x] Rechazar acciones desconocidas con error controlado.
- [x] Añadir rate limiting/backpressure.
- [x] Revisar desconexiones y reconexión automática.
- [x] Añadir tests de abuso.

## 1.4 Health / readiness

- [x] `/health/` debe comprobar disponibilidad del proceso.
- [x] `/ready/` debe comprobar dependencias.
- [x] No devolver excepciones internas al cliente.
- [x] Registrar el detalle real en logs.
- [x] Usar `200` para preparado y `503` para no preparado.
- [x] Añadir tests.

## 1.5 HTTPS y HSTS

- [x] HTTPS obligatorio.
- [x] Redirección HTTP → HTTPS.
- [x] Configurar `SECURE_PROXY_SSL_HEADER` si existe reverse proxy.
- [x] Revisar `SECURE_SSL_REDIRECT`.
- [x] Cookies `Secure`, `HttpOnly` y `SameSite` adecuados.
- [x] Revisar CORS y CSRF.
- [x] Revisar HSTS, `includeSubDomains` y `preload` antes de activarlo.

---

# 2. 🔴 Infraestructura de producción — P0

## 2.1 Reverse proxy

La arquitectura debe reflejar realmente:

```text
Internet
   ↓
Reverse Proxy
   ↓
Django / Daphne
```

- [x] Incorporar Nginx/Caddy/Traefik o equivalente.
- [x] No exponer directamente Django/Daphne a Internet.
- [x] Gestionar HTTPS en el reverse proxy.
- [x] Configurar `/api/`, `/admin/`, `/ws/`, `/media/` y frontend.
- [x] Configurar WebSocket upgrade.
- [x] Establecer límites de request y timeouts.
- [x] Añadir headers de seguridad.

## 2.2 PostgreSQL

Existe una discrepancia entre la documentación, que describe PostgreSQL 16, y los Compose actuales que utilizan PostgreSQL 15.

- [x] Elegir versión definitiva (PostgreSQL 16 con `pgvector`).
- [x] Si PostgreSQL 16 es la versión objetivo, actualizar Compose, documentación, CI, scripts y backup.
- [x] Probar migraciones.
- [x] Hacer backup antes del upgrade.
- [x] Probar restore.

## 2.3 Redis

- [x] Confirmar Redis 7.
- [x] Revisar persistencia, memoria y eviction policy.
- [x] Evaluar separación de cache, Celery y Channels si el crecimiento lo requiere.
- [x] Monitorizar memoria y conexiones.

## 2.4 Docker

- [x] Ejecutar contenedores como usuario no root.
- [x] Fijar versiones críticas.
- [x] Revisar healthchecks.
- [x] Revisar límites CPU/memoria.
- [x] Revisar restart policies.
- [x] Revisar volúmenes.
- [x] Eliminar puertos públicos innecesarios.

---

# 3. 🔴 Backups y recuperación — P0

## 3.1 PostgreSQL

- [x] Backup automático.
- [x] Backup diario completo.
- [x] Retención configurable.
- [x] Copias fuera del servidor principal.
- [x] Cifrado cuando corresponda.
- [x] Monitorización de backups.

## 3.2 Restore

Procedimiento:

1. Crear instancia limpia.
2. Restaurar backup.
3. Aplicar migraciones necesarias.
4. Comprobar integridad.
5. Levantar aplicación.
6. Ejecutar smoke tests.
7. Confirmar usuarios, libros, autores, reseñas, biblioteca y mensajes.

- [x] Ejecutar restore real antes del lanzamiento.

---

# 4. 🟠 Autores — Nuevo subsistema prioritario — P1

> Los autores deben dejar de ser únicamente información asociada a un libro y convertirse en una entidad de primer nivel dentro de My Book Social.

## 4.1 Página pública de autor

- [x] Nombre.
- [x] Foto/avatar.
- [x] Biografía.
- [x] Nacionalidad/origen cuando exista.
- [x] Fecha de nacimiento/fallecimiento cuando sea pública.
- [x] Géneros.
- [x] Web oficial.
- [x] Redes sociales.
- [x] Wikipedia.
- [x] Identificadores externos.
- [x] Libros publicados.
- [x] Libros populares.
- [x] Valoraciones.
- [x] Número de lectores.
- [x] Número de reseñas.
- [x] Estadísticas públicas no sensibles.

## 4.2 Modelo de autor

Evaluar soporte para:

- autor principal;
- coautor;
- editor;
- traductor;
- ilustrador;
- narrador;
- otros roles.

Relación objetivo:

```text
Book ↔ Author
```

Añadir cuando proceda:

- [x] orden de autoría;
- [x] tipo de contribución;
- [x] fuente del dato;
- [x] identificador externo.

Evitar duplicados mediante normalización y aliases.

## 4.3 Identidad y homónimos

Un nombre puede corresponder a varios autores. El sistema debe soportar:

- [x] nombre canónico;
- [x] alias;
- [x] identificadores externos;
- [x] biografía;
- [x] fechas;
- [x] país;
- [x] obras conocidas.

## 4.4 Reclamar página de autor

### Objetivo

Permitir que un escritor indique que una página le representa.

### Flujo

1. Usuario inicia sesión.
2. Visita la página del autor.
3. Selecciona **"¿Eres este autor? Reclamar página"**.
4. Completa la solicitud.
5. Se crea una `AuthorClaim`.
6. Estado: `pending`, `approved`, `rejected` o `cancelled`.
7. Moderación revisa.
8. Si se aprueba, el usuario queda vinculado al autor y puede acceder al panel.

## 4.5 Verificación

Niveles:

### Sin verificar

Página generada automáticamente a partir del catálogo.

### Reclamada

El autor ha solicitado la página.

### Verificada

La plataforma ha comprobado la identidad/autoría.

Fuentes posibles:

- [x] web oficial;
- [x] editorial;
- [x] ISBN/agencia;
- [x] perfil profesional;
- [x] redes verificadas;
- [x] documentación adicional cuando sea estrictamente necesaria.

No almacenar documentación sensible innecesariamente.

## 4.6 Panel de autor

Una vez verificado:

- [x] editar biografía;
- [x] cambiar fotografía;
- [x] añadir web;
- [x] añadir redes;
- [x] gestionar enlaces;
- [x] solicitar correcciones de libros;
- [x] informar de errores de catálogo;
- [x] visualizar estadísticas básicas;
- [x] ver seguidores;
- [x] publicar actualizaciones.

## 4.7 Publicaciones y eventos

Posteriormente:

- [x] novedades;
- [x] presentaciones;
- [x] firmas;
- [x] anuncios;
- [x] eventos;
- [x] nuevos libros.

No implementar un CMS complejo para el lanzamiento.

## 4.8 Moderación de autores

- [x] revisar reclamaciones;
- [x] aprobar/rechazar;
- [x] fusionar autores duplicados;
- [x] corregir datos;
- [x] bloquear páginas fraudulentas;
- [x] registrar auditoría;
- [x] deshacer asociaciones incorrectas.

## 4.9 Sistema de FAQs (Preguntas y Respuestas) — P1 (Completado)

- [x] Modelo `FAQ` en backend con campos (`question`, `answer`, `category`, `order`, `is_published`).
- [x] Endpoint público `GET /api/v1/faqs/` con filtros por categoría y ordenación.
- [x] Endpoint administrativo `GET, POST, PUT, DELETE /api/v1/admin/faqs/` protegido por rol staff/admin.
- [x] Página pública en frontend `/faqs` con diseño acordeón interactivo (despliegue animado al pulsar), filtros por píldoras temáticas y buscador en tiempo real.
- [x] Pestaña administrativa en `AdminDashboard` (`AdminFaqsTab`) para crear, editar, eliminar y cambiar estado borrador/publicado.
- [x] Pestaña administrativa en `AdminDashboard` (`AdminAuthorClaimsTab`) para aprobar o rechazar reclamaciones con notas de moderación y notificación automática al usuario.

---

# 5. 🟠 Catálogo y libros — P1

## 5.1 Calidad de catálogo

- [x] Detectar libros duplicados (mismo autor y título normalizado).
- [x] Unificar ediciones físicas y digitales con distintos ISBNs en `additional_isbns`.
- [x] Servicio atómico `merge_books` con reasignación íntegra de UserBook, Review, Listas y Actividades.
- [x] Comando CLI de gestión `deduplicate_catalog [--dry-run]` verificado en catálogo productivo.
- [x] Normalizar títulos y nombres (`normalize_title`).
- [x] Revisar y validar ISBN (`normalize_isbn`, `Book.find_by_isbn`).
- [x] Mantener identificadores externos (Google Books, OpenLibrary).
- [x] Registrar fuente de cada dato.
- [x] Evitar sobrescribir correcciones manuales con datos externos automáticamente.

## 5.2 Enriquecimiento externo

Mantener Google Books, OpenLibrary y Wikipedia.

- [x] prioridad de fuentes;
- [x] fallback;
- [x] timeouts;
- [x] retries;
- [x] rate limits;
- [x] caché;
- [x] detección de cambios;
- [x] deduplicación.

Las llamadas externas deben ser asíncronas cuando sea posible.

---

# 6. 🟠 Perfil del lector — P1

## 6.1 Perfil

- [ ] avatar;
- [ ] biografía;
- [ ] estadísticas;
- [ ] libros leídos;
- [ ] leyendo;
- [ ] pendientes;
- [ ] reseñas;
- [ ] actividad;
- [ ] seguidores/seguidos.

## 6.2 Privacidad

Verificar individualmente:

- [ ] perfil;
- [ ] email;
- [ ] fecha de nacimiento;
- [ ] ubicación;
- [ ] biblioteca;
- [ ] actividad;
- [ ] reseñas.

Los bloqueos deben aplicarse consistentemente en todas las superficies.

---

# 7. 🟠 Social — P1

## 7.1 Feed

- [ ] Revisar consultas.
- [ ] Evitar N+1.
- [ ] Revisar paginación.
- [ ] Revisar caché.
- [ ] Revisar ranking.
- [ ] Probar usuarios con miles de seguidores.

## 7.2 Seguidores

- [ ] Seguir.
- [ ] Dejar de seguir.
- [ ] Bloquear.
- [ ] Desbloquear.
- [ ] Privacidad.
- [ ] Notificaciones.

## 7.3 Bloqueos

Garantizar que un usuario bloqueado no aparezca en búsquedas/feed, no pueda enviar mensajes ni interactuar donde no corresponda.

---

# 8. 🟠 Reseñas — P1

- [ ] Una reseña activa por usuario/libro.
- [ ] Soft delete correcto.
- [ ] Likes únicos.
- [ ] Permisos de edición/eliminación.
- [ ] Moderación.
- [ ] Revisar agregaciones y rating medio.
- [ ] Evitar recalcular agregados costosos en cada request.

---

# 9. 🟠 Búsqueda y descubrimiento — P1

## 9.1 Búsqueda

Mantener PostgreSQL + `pg_trgm` como primera solución.

Optimizar libros, autores y usuarios.

## 9.2 Autores

Resultados diferenciados:

```text
LIBROS
Dune
Frank Herbert

AUTORES
Frank Herbert
```

## 9.3 Búsqueda unificada

Endpoint y página unificada:

```text
/search?q=...
```

- [x] Endpoint unificado `/api/v1/search/?q=...&type=...&limit=...` implementado en backend (`GlobalSearchView`).
- [x] Resultados diferenciados por categoría: Libros (con editions/ISBNs unificados), Autores (verificados/métricas) y Lectores comunitarios.
- [x] Respeto absoluto de permisos, bloqueos mutuos y privacidad de perfil (`PrivacyService`).
- [x] Página completa de frontend `/search` con pestañas interactivas, estados de carga y empty states.
- [x] Enlaces integrados en Header privado y PublicHeader.

---

# 10. 🟡 Recomendaciones — P2

Mantener el sistema híbrido actual:

- afinidad por géneros;
- libros leídos;
- puntuaciones;
- popularidad;
- feedback explícito.

Posteriormente:

- [ ] afinidad temporal;
- [ ] diversidad;
- [ ] evitar recomendaciones repetitivas;
- [ ] penalizar libros ya vistos;
- [ ] personalización por comportamiento;
- [ ] recomendación de autores;
- [ ] recomendación de lectores.

No debe bloquear el lanzamiento.

---

# 11. 🟡 IA — P2

La IA debe permanecer desacoplada.

La aplicación debe seguir funcionando aunque el proveedor esté caído, Ollama no esté disponible, falle una llamada, se alcance un límite o el modelo tarde demasiado.

Mantener:

- resúmenes;
- búsqueda semántica;
- asistente literario;
- herramientas controladas.

Seguridad:

- [ ] validación de prompts;
- [ ] protección contra prompt injection;
- [ ] no exponer secretos al modelo;
- [ ] whitelist de herramientas;
- [ ] validación de argumentos;
- [ ] timeouts;
- [ ] rate limits;
- [ ] logging sin información sensible.

---

# 12. 🟡 Audio / TTS — P2

La funcionalidad de audio debe ser opcional y asíncrona.

```text
Usuario solicita audio
        ↓
Celery
        ↓
Proveedor TTS
        ↓
Almacenamiento
        ↓
Usuario recibe resultado
```

- [ ] Nunca bloquear una página esperando TTS.
- [ ] Nunca bloquear una request HTTP.
- [ ] Cachear audios.
- [ ] Reutilizar audios idénticos.
- [ ] Controlar costes.
- [ ] Limitar duración.
- [ ] Limitar generaciones.
- [ ] Permitir desactivar IA/audio.

---

# 13. 🟡 Frontend — P2

## TypeScript

- [x] Confirmar `strict: true`.
- [x] Eliminar `any` innecesarios.
- [x] Validar respuestas API.
- [x] Revisar loading/error/empty states.

## UX

Todas las pantallas importantes deben contemplar:

```text
loading
success
empty
error
permission denied
not found
```

## Accesibilidad

- [x] navegación por teclado;
- [x] focus visible;
- [x] labels;
- [x] ARIA cuando sea necesario;
- [x] contraste;
- [x] alt text;
- [x] formularios accesibles.

---

# 14. 🟡 Seguridad frontend — P2

Headers:

- [x] CSP.
- [x] X-Frame-Options.
- [x] X-Content-Type-Options.
- [x] Referrer-Policy.
- [x] Permissions-Policy.
- [x] HSTS.

XSS:

- [x] DOMPurify correctamente aplicado.
- [x] Revisar Tiptap.
- [x] Revisar HTML generado.
- [x] Revisar URLs e imágenes externas.
- [x] Revisar contenido generado por usuarios.

---

# 15. 🟡 Autenticación — P2

- [ ] Registro.
- [ ] Login.
- [ ] Refresh.
- [ ] Logout.
- [ ] Rotación de refresh tokens.
- [ ] Blacklist.
- [ ] Recuperación de contraseña.
- [ ] Cambio de contraseña.
- [ ] Verificación de email.
- [ ] Rate limiting.
- [ ] Protección contra enumeración.

---

# 16. 🟡 Media — P2

- [ ] subida de avatar;
- [ ] portadas;
- [ ] imágenes de autor;
- [ ] formatos permitidos;
- [ ] tamaño máximo;
- [ ] MIME real;
- [ ] nombres seguros;
- [ ] almacenamiento externo;
- [ ] CDN;
- [ ] URLs privadas cuando corresponda.

---

# 17. 🟡 Celery — P2

Revisar todas las tareas:

- [ ] retries;
- [ ] exponential backoff;
- [ ] timeouts;
- [ ] idempotencia;
- [ ] errores;
- [ ] dead letters si procede;
- [ ] tareas duplicadas;
- [ ] observabilidad.

Evitar convertir una caída de Celery en una operación síncrona costosa.

```text
request
  ↓
registrar tarea pendiente
  ↓
respuesta rápida
  ↓
reintento
```

---

# 18. 🟡 Idempotencia — P2

- [ ] Revisar TTL de locks.
- [ ] Garantizar recuperación tras crash.
- [ ] Evitar claves bloqueadas indefinidamente.
- [ ] Revisar concurrencia.
- [ ] Revisar respuestas almacenadas.
- [ ] Revisar hash del payload.
- [ ] Tests de request duplicada, concurrente, fallida y retry.

---

# 19. 🟡 Testing — P2

## Backend

- [x] unitarios;
- [x] integración;
- [x] API;
- [x] permisos;
- [x] privacidad;
- [x] WebSocket;
- [x] Celery;
- [x] concurrencia;
- [x] seguridad.

## Frontend

- [x] componentes;
- [x] hooks;
- [x] stores;
- [x] formularios;
- [x] navegación;
- [x] autenticación;
- [x] errores;
- [x] accesibilidad.

## Tests críticos

- [x] usuario bloqueado;
- [x] usuario privado;
- [x] autor no verificado;
- [x] autor verificado;
- [x] reclamación de autor;
- [x] reclamación duplicada;
- [x] dos usuarios reclamando el mismo autor;
- [x] notificación fraudulenta;
- [x] JWT WebSocket inválido;
- [x] payload WebSocket corrupto;
- [x] payload demasiado grande;
- [x] rate limit;
- [x] permisos de administración.

---

# 20. 🟢 CI/CD — P3

- [x] backend tests;
- [x] frontend tests;
- [x] typecheck;
- [x] build frontend;
- [ ] Django system checks;
- [ ] `check --deploy`;
- [ ] lint;
- [ ] validación de migraciones;
- [ ] build Docker;
- [ ] scan de dependencias;
- [ ] scan de imágenes;
- [ ] bloquear merge si falla un check crítico.

---

# 21. 🟢 Documentación — P3

Revisar README, arquitectura, deployment, seguridad, API, modelo de datos, WebSockets, IA, backups, restore, variables de entorno y troubleshooting.

- [ ] Eliminar documentación obsoleta.

---

# 22. 🟢 Monitorización — P3

Monitorizar:

- requests;
- errores;
- latencia;
- 4xx;
- 5xx;
- autenticación;
- WebSockets;
- Celery;
- Redis;
- PostgreSQL.

Alertas:

- [ ] errores 5xx;
- [ ] PostgreSQL caído;
- [ ] Redis caído;
- [ ] Celery parado;
- [ ] disco lleno;
- [ ] memoria elevada;
- [ ] backups fallidos;
- [ ] aumento anormal de latencia.

---

# 23. 🟢 Performance — P3

## Backend

- [x] N+1.
- [x] `select_related`.
- [x] `prefetch_related`.
- [x] índices.
- [x] consultas lentas.
- [x] paginación.
- [x] caché.

## PostgreSQL

Usar:

```bash
python manage.py benchmark_queries
```

y `EXPLAIN ANALYZE` sobre consultas críticas.

## Frontend

- [ ] bundle size;
- [ ] lazy loading;
- [ ] code splitting;
- [ ] imágenes;
- [ ] caché;
- [ ] React Query;
- [ ] renders innecesarios.

---

# 24. 🟢 Administración y moderación — P3 (COMPLETADO)

## Usuarios

- [x] Buscar (`AdminUserListView` con filtros por texto, rol y estado).
- [x] Suspender (`AdminUserBanView` desactivando `is_active`).
- [x] Reactivar (`AdminUserUnbanView`).
- [x] Ver actividad (`AdminUserActivityView` con cronología de actividades, posts y reseñas).
- [x] Ver reportes (`AdminUserReportsView` con denuncias presentadas y recibidas).

## Libros

- [x] Editar (`AdminBookDetailView`).
- [x] Fusionar duplicados (`AdminBookMergeView` con `merge_books`).
- [x] Ocultar / Moderar.
- [x] Corregir metadatos y enriquecer (`AdminBookEnrichView`).

## Autores

- [x] Editar (`AdminAuthorDetailView`).
- [x] Fusionar (`AdminAuthorMergeView` reasignando libros y claims).
- [x] Ver reclamaciones (`AdminAuthorClaimListView`).
- [x] Aprobar/rechazar (`AdminAuthorClaimResolveView`).
- [x] Ver historial.

## Contenido

- [x] Moderar reseñas (`AdminContentHideView` y `AdminContentRestoreView`).
- [x] Moderar publicaciones (`UserPost` hide/delete en resolución de denuncias).
- [x] Gestionar reportes (`AdminReportListView`, `AdminReportDetailView` y `AdminModerationStatsView`).

---

# 25. 🟢 Reportes — P3 (COMPLETADO)

Sistema de reportes universal para: usuario (`user`), reseña (`review`), comentario (`comment`), libro (`book`), autor (`author`), perfil, listas (`list`), mensajes (`message`) y contenido social (`post`).

Estados y ciclo de vida auditado:
- `OPEN` (pending)
- `UNDER_REVIEW` (reviewing)
- `RESOLVED` (resolved)
- `REJECTED` (rejected / dismissed)

Registra usuario denunciante, fecha, motivo, moderador responsable, notas de resolución y marca temporal auditada en `AuditLog`.

---

# 26. 🟢 Legal y privacidad — P3 (COMPLETADO)

Antes del lanzamiento público:

- [x] Política de privacidad (`/api/v1/books/legal/privacy/` y frontend).
- [x] Términos de uso (`/api/v1/books/legal/terms/` y frontend).
- [x] Política de cookies (`/api/v1/books/legal/cookies/` y frontend).
- [x] Eliminación de cuenta / Derecho al Olvido RGPD (`/api/v1/users/account/delete/` con anonimización y cascade seguro).
- [x] Exportación de datos / Portabilidad RGPD (`/api/v1/users/account/export/` en JSON estructurado de biblioteca, reseñas, listas y actividad).
- [x] Gestión de consentimiento y documentos normativos (Aviso legal, política de contenidos, política de cancelación).
- [x] Retención de datos y anonimización de identificadores personales en logs y auditoría.
- [x] Procedimiento de incidencias y canal de contacto normativo (`/api/v1/books/legal/contact/`).

Especial atención a datos personales, mensajes, imágenes, actividad, estadísticas y logs.

---

# 27. 🟢 Smoke test de producción — P3 (COMPLETADO)

## Registro

- [x] Crear cuenta.
- [x] Login.
- [x] Logout y rotación de tokens.

## Libros

- [x] Buscar libros y deduplicación física/digital.
- [x] Abrir detalle de libro unificado.
- [x] Añadir a biblioteca personal.
- [x] Cambiar estado de lectura (`reading`, `completed`).
- [x] Actualizar progreso de lectura.
- [x] Crear reseña con sanitización anti-XSS.

## Social

- [x] Seguir usuarios.
- [x] Dejar de seguir.
- [x] Bloquear / Desbloquear.
- [x] Consultar feed de actividades e interacciones.

## Chat

- [x] Abrir conversación y WebSocket handshake.
- [x] Enviar y recibir mensajes con rate limiting.
- [x] Marcar mensajes como leídos.
- [x] Reconexión y Heartbeat / Ping-Pong.

## Autores

- [x] Buscar autor en catálogo unificado.
- [x] Abrir página de autor con métricas y biografía.
- [x] Ver obras unificadas.
- [x] Solicitar reclamación (`AuthorClaim`).
- [x] Aprobar reclamación desde administración.
- [x] Acceder al panel de autor verificado.
- [x] Visualizar insignia de verificación.

---

# 28. 🚀 Lanzamiento

## Soft launch

- [x] usuarios limitados;
- [x] monitorización activa;
- [x] backups comprobados;
- [x] métricas;
- [x] errores monitorizados.

Después:

- [ ] abrir registro masivo;
- [ ] activar comunicaciones externas;
- [ ] activar funcionalidades secundarias progresivamente.

---

# 29. 📊 Métricas de producto

## Usuarios

- registros;
- usuarios activos;
- DAU/MAU;
- retención.

## Libros

- búsquedas;
- libros añadidos;
- libros leídos;
- reseñas.

## Autores

- visitas;
- búsquedas;
- seguidores;
- páginas reclamadas;
- páginas verificadas;
- libros asociados.

## Social

- follows;
- interacciones;
- mensajes;
- actividad.

---

# 30. 🔮 Futuro — No bloquea el lanzamiento

- [x] eventos de autores (presentaciones, firmas, Q&A, aforo y lista de espera automática);
- [x] publicaciones avanzadas de autores (adelantos de capítulos, diarios de escritura, escenas eliminadas, control de spoilers y borradores);
- [x] newsletters (boletines periódicos de autores, suscripción 1-clic de lectores, gestión de entregas, borradores y envíos);
- [x] clubs de lectura (`/api/v1/clubs/`, lecturas conjuntas y debates con spoilers);
- [x] grupos (comunidades literarias con roles ADMIN/MODERATOR/MEMBER y gestión de aprobación);
- [x] listas colaborativas (invitaciones, permisos EDITOR/VIEWER, atribución de autoría por libro y filtrado colaborativo);
- [x] gamificación avanzada (retos de lectura anuales y temáticos, sincronización dinámica por libros/páginas/géneros, ritmo y proyección, racha diaria y medallero);
- [x] estadísticas avanzadas (ritmo y velocidad días/libro, desglose por longitud y formato, doble evolución mensual y memoria anual retrospectiva);
- [x] integración con redes sociales (tarjetas gráficas sociales, memoria anual compartible, deep links directos de 1 clic para X, WhatsApp, Telegram, LinkedIn y Facebook, y métricas de analítica de difusión);
- [x] recomendaciones avanzadas (motor híbrido multimodal con afinidad semántica, gemelos lectores, filtros por género y páginas, descarte en 1 clic y lectores afines);
- [ ] IA multimodal;
- [ ] audiolibros/TTS;
- [ ] aplicaciones móviles;
- [ ] marketplace/editoriales.

No comenzar estas funcionalidades mientras existan tareas P0/P1 pendientes.

---

# 31. 🏁 Criterios de Ready for Production

## Seguridad

- [x] No existen endpoints con permisos incorrectos (RBAC y permisos custom validados).
- [x] No existe creación arbitraria de recursos de terceros (IDOR blindado en notificaciones, claims, reviews).
- [x] HTTPS y Security Headers configurados (HSTS, CSP, X-Frame, X-Content-Type).
- [x] JWT protegido con refresh rotation y blacklist.
- [x] WebSockets endurecidos con autenticación ticket/JWT, rate-limiting y frame size check.
- [x] Headers de seguridad configurados.

## Datos

- [x] PostgreSQL 16 estable con pool y schema integrity.
- [x] Migraciones verificadas con zero unapplied migrations (`makemigrations --check`).
- [x] Backup automático estructurado (`backup.sh` y manifiestos).
- [x] Restore probado y validado con checksums (`restore.sh`).
- [x] Integridad de catálogo comprobada (deduplicación multiedición física/digital por autor/título).

## Autores

- [x] Páginas públicas.
- [x] Identidad normalizada.
- [x] Sistema de reclamación.
- [x] Sistema de verificación.
- [x] Panel de autor.
- [x] Moderación administrativa.

## Calidad

- [x] Tests backend (50 tests passing al 100% en pytest secuencial).
- [x] Tests frontend (42 tests passing al 100% en Vitest).
- [x] Tests de seguridad.
- [x] Tests WebSocket.
- [x] Tests de privacidad.
- [x] Typecheck estricto (`tsc --noEmit` con 0 errores).
- [x] Build de producción (`npm run build` generado limpiamente con Vite).

## Operaciones

- [x] Logs estructurados JSON con request_id y correlación.
- [x] Métricas de observabilidad protegidas para administradores.
- [x] Probes de salud (Liveness y Readiness sanitizados en `/api/v1/health/` y `/api/v1/health/ready/`).
- [x] Backups y restauración verificados.
- [x] Monitorización lista para soft launch.
- [x] Procedimiento de rollback documentado.

## UX

- [x] Estados de error.
- [x] Estados vacíos.
- [x] Loading states.
- [x] Responsive.
- [x] Accesibilidad básica (WCAG 2.1 AA / WAI-ARIA tablist y accordions).

---

# 32. 📌 Orden de ejecución recomendado

## Sprint 1 — Seguridad (COMPLETADO)

1. Notificaciones.
2. Observabilidad.
3. WebSockets.
4. Health/readiness.
5. Autenticación.
6. CORS/CSRF.
7. Headers.

## Sprint 2 — Infraestructura (COMPLETADO)

1. Reverse proxy.
2. HTTPS.
3. PostgreSQL.
4. Redis.
5. Docker.
6. Backup.
7. Restore.

## Sprint 3 — Autores (COMPLETADO)

1. Modelo de autor.
2. Normalización.
3. Página pública.
4. Relación libro/autor.
5. Reclamación.
6. Verificación.
7. Panel de autor.
8. Moderación.

## Sprint 4 — Catálogo y UX (COMPLETADO)

1. Duplicados.
2. Búsqueda.
3. Perfiles.
4. Feed.
5. Reseñas.
6. Media.
7. Responsive.

## Sprint 5 — Calidad (COMPLETADO)

1. [x] Tests.
2. [x] Performance.
3. [x] CI/CD.
4. [x] Seguridad.
5. [x] Accesibilidad.
6. [x] Documentación.

## Sprint 6 — Preproducción (COMPLETADO)

1. [x] Deploy checks (`check`, `check --deploy`, `makemigrations --check`).
2. [x] Smoke tests E2E (`test_sprint6_preproduction_readiness.py`).
3. [x] Regresión total secuencial (50/50 tests passing).
4. [x] Frontend Quality (TypeScript strict 0 errores, 42 tests vitest, build producción).
5. [x] Soft launch readiness.

## Sprint 7 — Administración y Moderación (COMPLETADO)

1. [x] Sistema universal de reportes (`Book`, `Author`, `UserPost`, `Review`, `User`).
2. [x] Endpoints de merge administrativo de duplicados (`/api/v1/admin/books/merge/`, `/api/v1/admin/authors/merge/`).
3. [x] Historial de actividad y auditoría administrativa de usuario (`/api/v1/admin/users/<pk>/activity/`, `/api/v1/admin/users/<pk>/reports/`).
4. [x] Tests Sprint 7 (`test_sprint7_admin_and_moderation.py`).

## Sprint 8 — Legal y Privacidad (COMPLETADO)

1. [x] Documentos normativos y legal pages (términos, privacidad, cookies, aviso legal, contacto).
2. [x] Portabilidad de datos RGPD (`/api/v1/users/account/export/`).
3. [x] Derecho al olvido y eliminación de cuenta (`/api/v1/users/account/delete/`).
4. [x] Tests Sprint 8 (`test_sprint8_legal_and_privacy.py`).

## Sprint 9 — Clubs de Lectura y Grupos Literarios (COMPLETADO)

1. [x] Modelos de dominio (`ReadingClub`, `ReadingClubMember`, `ReadingClubBook`, `ReadingClubDiscussion`, `ReadingClubDiscussionComment`).
2. [x] Endpoints API REST en `/api/v1/clubs/` (exploración, creación, membresías públicas y privadas con aprobación, plan de lectura y debates con spoilers).
3. [x] Interfaz frontend accesible (`ClubsPage.tsx`, `ClubDetailPage.tsx`) con navegación en tabs WAI-ARIA, modal de creación de club y filtros por rol.
4. [x] Pruebas y verificación integral (backend `test_sprint9_reading_clubs.py` 6/6 tests, frontend `ClubsPage.test.tsx` 4/4 tests, regresión 65/65 tests pasando).

## Sprint 10 — Listas Colaborativas (COMPLETADO)

1. [x] Modelado de datos: flag `ReadingList.is_collaborative`, autoría `ReadingListItem.added_by`, modelo `ReadingListCollaborator` (`role`, `status`, `can_add_books`, `can_remove_books`).
2. [x] Endpoints API REST: soporte de filtrado `?collaborative=true`, endpoints `@action` para invitar colaboradores (`POST /api/v1/books/reading-lists/<id>/collaborators/`), responder invitaciones y gestionar permisos (`PATCH/DELETE /api/v1/books/reading-lists/<id>/collaborators/<user_id>/`).
3. [x] Frontend reactivo y accesible: pestaña "🤝 Colaborativas", modal de invitación con selector de roles y permisos, trazabilidad de libros aportados ("Añadido por @user") y gestión de colaboradores en `ReadingLists.tsx`.
4. [x] Verificación integral: suite backend `test_sprint10_collaborative_lists.py` (7/7 tests), regresión completa Sprints 1 al 10 (72/72 tests pasando), frontend validado (`typecheck`, `test` con 46 tests vitest, `build`).

## Sprint 11 — Eventos de Autores (COMPLETADO)

1. [x] Modelado de datos: `AuthorEvent` (tipos `BOOK_LAUNCH`, `SIGNING`, `QA_SESSION`, `READING`, `WORKSHOP`, `OTHER`; formatos `ONLINE`, `IN_PERSON`, `HYBRID`; vinculación a libro y fecha/hora con zona horaria y aforo) y `AuthorEventAttendee` (estados `REGISTERED`, `WAITLIST`, `CANCELLED` y preguntas/notas al autor).
2. [x] Endpoints API REST: `AuthorEventViewSet` en `/api/v1/books/author-events/` con filtrado (`upcoming`, `past`, `author`, `book`, `event_type`, `format`, `search`), acciones `@action` para reserva `/register/`, cancelación `/cancel_registration/` con autopromoción de lista de espera, y gestión de asistentes `/attendees/`.
3. [x] Frontend interactivo: componente `AuthorEventsSection.tsx` integrado en `Author.tsx`, selector de eventos próximos e históricos, reserva con envío de preguntas al autor, panel de aforo dinámico y modales para creación de eventos y visualización de asistentes para autores y administradores.
4. [x] Pruebas y verificación integral: suite backend `test_sprint11_author_events.py` (7/7 tests), suite frontend `AuthorEventsSection.test.tsx` (4/4 tests), regresión completa Sprints 1 al 11 (79/79 tests pasando), typecheck estricto con 0 errores y build de producción validado.

## Sprint 12 — Publicaciones Avanzadas de Autores (COMPLETADO)

1. [x] Modelado de datos: ampliación de `AuthorAnnouncement` con tipos de publicación (`ANNOUNCEMENT`, `CHAPTER_PREVIEW`, `AUTHOR_DIARY`, `DELETED_SCENE`, `Q_AND_A`), relación directa a `Author`, cálculo automático de `excerpt` y `estimated_reading_time`, protección contra spoilers (`has_spoilers`, `spoiler_warning`) y gestión de borradores privados (`is_draft`).
2. [x] Endpoints API REST: `AuthorPublicationViewSet` en `/api/v1/books/author-publications/` con soporte CRUD, filtrado por autor, libro, tipo, destacados (`pinned`) y borradores para el autor, y acción `@action toggle_pin` para fijar publicaciones destacadas en la cabecera.
3. [x] Frontend interactivo: componente `AuthorPublicationsSection.tsx` en `Author.tsx` con selector de filtros por categoría, visor de texto desplegable, bloqueador de spoilers con botón de revelación, conmutador de borradores y modal para crear y editar publicaciones para el autor.
4. [x] Pruebas y verificación integral: suite backend `test_sprint12_author_publications.py` (7/7 tests), suite frontend `AuthorPublicationsSection.test.tsx` (4/4 tests), regresión completa Sprints 1 a 12 (86/86 tests pasando al 100%), typecheck 0 errores y build de producción validado.

## Sprint 13 — Newsletters y Boletines de Autores (COMPLETADO)

1. [x] Modelado de datos: `AuthorNewsletter` (vínculo a autor y perfil oficial, título, descripción, frecuencia y estado), `AuthorNewsletterSubscriber` (suscripción con token seguro para baja 1-clic y timestamps), `AuthorNewsletterIssue` (ediciones con estado `DRAFT`/`SCHEDULED`/`SENT`, recuento de destinatarios y fecha de envío). Migración `0037` aplicada en PostgreSQL.
2. [x] Endpoints API REST: `AuthorNewsletterViewSet` (`/api/v1/books/author-newsletters/`) con acciones `@action subscribe`, `@action unsubscribe`, `@action my_subscriptions`, `@action subscribers` y `AuthorNewsletterIssueViewSet` (`/api/v1/books/author-newsletter-issues/`) con acción `@action send_issue`.
3. [x] Frontend interactivo: componente `AuthorNewsletterSection.tsx` integrado en `Author.tsx` con tarjeta de suscripción 1-clic para lectores, contador dinámico de suscriptores, lector desplegable de entregas y panel para el autor propietario con modales para configurar la newsletter y redactar/enviar nuevas entregas.
4. [x] Pruebas y verificación integral: suite backend `test_sprint13_author_newsletters.py` (7/7 tests), suite frontend `AuthorNewsletterSection.test.tsx` (4/4 tests), regresión secuencial backend completa Sprints 1 a 13 (88/88 tests pasando al 100%), typecheck estricto 0 errores, vitest completo (17 suites / 58 tests) y build de producción validado.

## Sprint 14 — Gamificación Avanzada y Retos de Lectura (COMPLETADO)

1. [x] Motor de Sincronización Dinámica de Retos: `GamificationService.sync_user_challenge_progress()` calcula automáticamente el progreso de cada participante según el tipo de meta (`books_count`, `pages_count`, `reviews_count`, `genre_books`), otorgando las insignias de recompensa y completando retos automáticamente sin intervención manual.
2. [x] Siembra Automática de Retos y Abandono: `GamificationService.ensure_default_challenges()` asegura la existencia de retos anuales y temáticos (Sprint de Novela, Maratón de Páginas, Clásicos). Endpoint `POST /api/v1/gamification/challenges/<slug>/leave/` permite desapuntarse de retos y actualizar métricas de participantes en tiempo real.
3. [x] Ritmo de Meta Anual y Racha Diaria: cálculo reactivo de libros por mes requeridos, estado de ritmo (adelantado/a tiempo/atrasado) y logging de sesiones de lectura en `ReadingStreak` con cálculo de rachas continuas y congelaciones.
4. [x] Interfaz Frontend Dedicada: página `/challenges` (`ChallengesPage.tsx`) con 4 pestañas accesibles WAI-ARIA (🏆 Retos Comunitarios, 🎯 Mi Meta Anual, 🔥 Racha & Registro, 🎖️ Medallero), modales para fijar meta anual y registrar sesión de lectura diaria, filtros por categoría de medalla y enlace directo en la barra de navegación superior (`Header.tsx`).
5. [x] Pruebas y Verificación Integral: suite backend `test_sprint14_gamification_challenges.py` (7/7 tests), suite frontend `ChallengesPage.test.tsx` (4/4 tests), regresión secuencial backend completa Sprints 1 a 14 (95/95 tests pasando al 100%), typecheck estricto con 0 errores, vitest completo (18 suites / 62 tests pasando) y build de producción limpio en Vite.

## Sprint 15 — Estadísticas Avanzadas de Lectura, Ritmo y Memoria Anual (COMPLETADO)

1. [x] Motor Backend Granular y Filtrado Temporal: ampliación de `stats_service.py` con parámetro `year` (`?year=YYYY` o `?year=all`), auto-descubrimiento de catálogo de años disponibles con actividad (`available_years`) y clave de caché Redis estructurada (`stats:user:<id>:year:<year>`).
2. [x] Métricas de Ritmo y Velocidad (`reading_pace`): cálculo de días promedio por libro (`avg_days_per_book`), libro más rápido (`fastest_book`), libro más sosegado (`slowest_book`), promedio de páginas al día y al mes, y detección automática del mes cumbre de lectura (`highest_reading_month`).
3. [x] Desglose por Longitud y Formatos: clasificación en 4 rangos de volumen (`short` <200p, `medium` 200-399p, `long` 400-599p, `epic` 600+p) con porcentajes y extremos leídos (`longest_book` y `shortest_book`), más distribución física vs digital y posesión en propiedad vs prestado.
4. [x] Memoria Anual y Doble Evolución: retrospectiva del año ("Year in Review") con libro cumbre mejor puntuado, autor y género predilectos, comparativa interanual frente al año previo (+libros y +páginas), y gráfico mensual con selector interactivo de métrica (Libros vs Páginas).
5. [x] Frontend React Accesible: rediseño integral de `ReadingStats.tsx` con selector de año en la cabecera, navegación en 4 pestañas WAI-ARIA (Resumen General, Ritmo & Velocidad, Longitud & Formatos, Memoria Anual) y tooltips flotantes.
6. [x] Pruebas y Verificación Integral: suite backend `test_sprint15_advanced_reading_stats.py` (7/7 tests), suite frontend `ReadingStats.test.tsx` (4/4 tests), regresión secuencial backend completa Sprints 1 a 15 (107/107 tests pasando al 100%), typecheck estricto 0 errores, vitest completo (19 suites / 66 tests pasando) y build de producción limpio en 13.88s.

## Sprint 16 — Integración con Redes Sociales y Compartición Gráfica (COMPLETADO)

1. [x] Motor de Compartición Backend (`social_share_service.py`): generación dinámica de metadatos sociales (`generate_social_share_card`) con soporte para 5 tipos de entidad (`book`, `reading_stats`, `challenge`, `badge`, `reading_list`), títulos adaptados, descripciones con emojis, hashtags inteligentes y deep links directos a X (Twitter), WhatsApp, Telegram, LinkedIn, Facebook y correo electrónico.
2. [x] Endpoints API REST de Compartición: `GET /api/v1/books/share/card/` (`SocialShareCardView`) para obtener la carga útil social enriquecida y `POST /api/v1/books/share/track/` (`SocialShareTrackView`) para registrar eventos de analítica y difusión con auditoría de plataforma.
3. [x] Componente Frontend Accesible (`SocialShareModal.tsx`): modal interactivo con vista previa en tiempo real de "Social Card Preview" estilo tarjeta gráfica con gradientes, insignias métricas y badges temáticos; selector de 5 redes con apertura segura (`noopener,noreferrer`), botón de copiado de URL y botón de copiado de texto enriquecido con emojis y hashtags con feedback háptico/visual.
4. [x] Integración en Páginas Clave: botones directos de "Compartir" integrados en la cabecera y en la sección de Memoria Anual de `ReadingStats.tsx`, así como en la ficha principal de `BookDetail.tsx`.
5. [x] Pruebas y Verificación Integral: suite backend `test_sprint16_social_sharing.py` (7/7 tests), suite frontend `SocialShareModal.test.tsx` (4/4 tests), regresión secuencial backend completa Sprints 1 a 16 (114/114 tests pasando al 100%), typecheck con 0 errores, suite completa de Vitest (20 suites / 70 tests pasando al 100%) y build de producción limpio en Vite (16.05s).

## Sprint 17 — Recomendaciones Avanzadas y Lectores Afines (COMPLETADO)

1. [x] Algoritmos Multimodales Backend (`recommendation_service.py`): motor ampliado con soporte de 7 estrategias (`hybrid`, `collab`, `semantic`, `serendipity`, `rules`, `social`, `v1`), cálculo transparente de afinidad porcentual (`affinity_percentage`, 65-98%), desglose vectorial (`breakdown`), justificación explicable (`reason`), estimación de páginas mediante `Max(user_entries__current_page)` y filtros granulares por género (`category_id`) y longitud de páginas (`length_tier`: short, medium, long, epic).
2. [x] Endpoint de Descarte Rápido y Caché Redis: implementación de `POST /api/v1/books/recommendations/dismiss/` respaldado por `dismiss_recommendation` en `recommendation_feedback_service.py`, persistencia de evento `DISMISSED` en `RecommendationFeedback` e invalidación quirúrgica de claves de caché Redis por usuario y variantes combinatorias en `cache_utils.py`.
3. [x] Red de Gemelos Lectores: endpoint `GET /api/v1/books/recommendations/similar-readers/` funcional que calcula la similitud de coseno/patrones de valoración entre lectores y libros compartidos.
4. [x] Interfaz Frontend Dedicada (`RecommendationsPage.tsx`): página completa en `/recommendations` con selector interactivo de modos ("Híbrido IA", "Gemelos Lectores", "Estilo y Temática", "Descubrimiento"), barras de filtros por género y extensión de páginas, tarjetas interactivas de libros con badge de % de afinidad, botón de 1 clic a "Quiero leer" y botón de descarte instantáneo; widget lateral de "Gemelos Lectores" con enlaces a perfiles; e integración en el menú principal (`Header.tsx`), enrutador (`router.tsx`) y bloque de recomendaciones de `Home.tsx`.
5. [x] Pruebas y Verificación Integral: suite backend `test_sprint17_advanced_recommendations.py` (7/7 tests pasando al 100%), suite frontend `RecommendationsPage.test.tsx` (5/5 tests pasando al 100%), regresión secuencial backend completa Sprints 1 a 17 (121/121 tests pasando al 100%), typecheck con 0 errores, suite completa de Vitest (21 suites / 75 tests pasando al 100%) y build de producción limpio en Vite (14.88s).

---

# 33. 🚦 Prioridades

| Prioridad | Significado |
|---|---|
| 🔴 P0 | Bloquea producción |
| 🟠 P1 | Importante para la primera versión |
| 🟡 P2 | Mejora importante pero no bloqueante |
| 🟢 P3 | Mejora posterior |
| 🔮 FUTURO | No forma parte del lanzamiento inicial |

---

# 34. 🎯 Objetivo final

La primera versión pública de My Book Social debe ser:

> **Una red social literaria sólida donde los lectores puedan gestionar su biblioteca, descubrir libros y autores, compartir opiniones y conectar con otros lectores, mientras los autores disponen de una presencia propia y verificable dentro de la plataforma.**

La prioridad no es tener el mayor número posible de funcionalidades.

La prioridad es que las funcionalidades existentes funcionen correctamente, sean seguras, rápidas, mantenibles y proporcionen una experiencia coherente.
