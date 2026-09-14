# Arquitectura del Sistema MyBookConnect

## 1. Introducción
MyBookConnect es una plataforma comunitaria para lectores, estructurada como una aplicación desacoplada que combina la solidez de un backend monolítico modular en Python/Django con una interfaz de usuario reactiva en React y TypeScript.

## 2. Componentes Clave
- **Cliente SPA:** React 18, Vite 6, TypeScript 5.9 (modo estricto), TailwindCSS 3.4 y Zustand para el manejo de estado de sesión.
- **API RESTful:** Django REST Framework 5.2 LTS, serialización tipada y documentación automática mediante `drf-spectacular` (OpenAPI 3.1).
- **Capa en Tiempo Real:** Django Channels 4 con Daphne (servidor ASGI) y Redis como capa de transporte de canales (`channels-redis`).
- **Base de Datos Principal:** PostgreSQL 16 con extensiones de trigramas (`pg_trgm`) para búsqueda difusa e índices GIN.
- **Caché y Mensajería:** Redis 7 para almacenamiento en caché de objetos, limitación de tasa (rate limiting) y broker de Celery.
- **Cola de Tareas Asíncronas:** Celery workers para tareas en segundo plano que evitan bloquear el hilo de petición HTTP.

## 3. Flujo de Datos Típico
1. El usuario interactúa con la interfaz React y despacha una acción (p. ej., marcar un libro como leído).
2. La petición HTTP viaja con la cabecera `Authorization: Bearer <access_token>` y `X-Request-ID`.
3. El `StructuredLoggingMiddleware` registra la entrada de la petición y cronometra su duración.
4. Django REST Framework valida permisos y ejecuta la lógica de negocio en la capa de servicios (`books.services`).
5. Se persiste la transacción en PostgreSQL con integridad referencial garantizada.
6. La caché de Redis para el libro y el usuario se invalida inmediatamente.
7. Se devuelve la respuesta JSON con la cabecera `X-Request-ID` al cliente.
