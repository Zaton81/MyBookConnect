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

# 24. 🟢 Administración y moderación — P3

## Usuarios

- [ ] Buscar.
- [ ] Suspender.
- [ ] Reactivar.
- [ ] Ver actividad.
- [ ] Ver reportes.

## Libros

- [ ] Editar.
- [ ] Fusionar duplicados.
- [ ] Ocultar.
- [ ] Corregir.

## Autores

- [ ] Editar.
- [ ] Fusionar.
- [ ] Ver reclamaciones.
- [ ] Aprobar/rechazar.
- [ ] Ver historial.

## Contenido

- [ ] Moderar reseñas.
- [ ] Moderar publicaciones.
- [ ] Gestionar reportes.

---

# 25. 🟢 Reportes — P3

Crear sistema de reportes para usuario, reseña, comentario, libro, autor, perfil y contenido.

Estados:

```text
pending
reviewing
resolved
rejected
```

Registrar usuario, fecha, motivo, moderador, resolución y timestamp.

---

# 26. 🟢 Legal y privacidad — P3

Antes del lanzamiento público:

- [ ] Política de privacidad.
- [ ] Términos de uso.
- [ ] Política de cookies si aplica.
- [ ] Eliminación de cuenta.
- [ ] Exportación de datos cuando corresponda.
- [ ] Gestión de consentimiento.
- [ ] Retención de datos.
- [ ] Procedimiento de incidencias.

Especial atención a datos personales, mensajes, imágenes, actividad, estadísticas y logs.

---

# 27. 🟢 Smoke test de producción — P3

## Registro

- [ ] Crear cuenta.
- [ ] Verificar email.
- [ ] Login.
- [ ] Logout.

## Libros

- [ ] Buscar.
- [ ] Abrir libro.
- [ ] Añadir a biblioteca.
- [ ] Cambiar estado.
- [ ] Añadir progreso.
- [ ] Crear reseña.

## Social

- [ ] Seguir.
- [ ] Dejar de seguir.
- [ ] Bloquear.
- [ ] Desbloquear.
- [ ] Ver feed.

## Chat

- [ ] Abrir conversación.
- [ ] Enviar mensaje.
- [ ] Recibir mensaje.
- [ ] Marcar leído.
- [ ] Reconectar.

## Autores

- [ ] Buscar autor.
- [ ] Abrir página.
- [ ] Ver libros.
- [ ] Solicitar reclamación.
- [ ] Aprobar reclamación desde administración.
- [ ] Acceder al panel de autor.
- [ ] Editar perfil.
- [ ] Ver insignia de verificación.

---

# 28. 🚀 Lanzamiento

## Soft launch

- [ ] usuarios limitados;
- [ ] monitorización activa;
- [ ] backups comprobados;
- [ ] métricas;
- [ ] errores monitorizados.

Después:

- [ ] abrir registro;
- [ ] activar comunicaciones;
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

- [ ] eventos de autores;
- [ ] publicaciones avanzadas de autores;
- [ ] newsletters;
- [ ] clubs de lectura;
- [ ] grupos;
- [ ] listas colaborativas;
- [ ] recomendaciones avanzadas;
- [ ] IA multimodal;
- [ ] audiolibros/TTS;
- [ ] estadísticas avanzadas;
- [ ] gamificación avanzada;
- [ ] aplicaciones móviles;
- [ ] integración con redes sociales;
- [ ] marketplace/editoriales.

No comenzar estas funcionalidades mientras existan tareas P0/P1 pendientes.

---

# 31. 🏁 Criterios de Ready for Production

## Seguridad

- [ ] No existen endpoints con permisos incorrectos.
- [ ] No existe creación arbitraria de recursos de terceros.
- [ ] HTTPS correctamente configurado.
- [ ] JWT protegido.
- [ ] WebSockets endurecidos.
- [ ] Headers de seguridad configurados.

## Datos

- [ ] PostgreSQL estable.
- [ ] Migraciones verificadas.
- [ ] Backup automático.
- [ ] Restore probado.
- [ ] Integridad de catálogo comprobada.

## Autores

- [x] Páginas públicas.
- [x] Identidad normalizada.
- [x] Sistema de reclamación.
- [x] Sistema de verificación.
- [x] Panel de autor.
- [x] Moderación administrativa.

## Calidad

- [x] Tests backend.
- [x] Tests frontend.
- [x] Tests de seguridad.
- [x] Tests WebSocket.
- [x] Tests de privacidad.
- [x] Typecheck.
- [x] Build de producción.

## Operaciones

- [ ] Logs.
- [ ] Métricas.
- [ ] Alertas.
- [ ] Backups.
- [ ] Monitorización.
- [ ] Procedimiento de rollback.

## UX

- [x] Estados de error.
- [x] Estados vacíos.
- [x] Loading states.
- [x] Responsive.
- [x] Accesibilidad básica.

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

## Sprint 6 — Preproducción

1. Deploy.
2. Smoke tests.
3. Backup/restore.
4. Monitorización.
5. Corrección de errores.
6. Soft launch.

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
