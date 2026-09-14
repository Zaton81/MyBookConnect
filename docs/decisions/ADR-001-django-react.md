# ADR-001: Desacoplamiento de Arquitectura con Django y React

## Estado
Aceptado

## Contexto
El proyecto requiere una plataforma web moderna, interactiva y de alto rendimiento que combine:
1. Una API backend robusta, segura y bien documentada con soporte para operaciones relacionales complejas, autenticación y WebSockets.
2. Una interfaz de usuario reactiva, fluida y con navegación rápida estilo SPA para lectores en escritorio y móviles.

## Decisión
Adoptar una arquitectura completamente desacoplada compuesta por:
- **Backend:** Python 5.2 LTS con Django REST Framework (DRF) y Django Channels sobre ASGI/WSGI.
- **Frontend:** Single-Page Application (SPA) desarrollada con React 18, TypeScript 5.9 en modo estricto, Vite 6 como empaquetador y TailwindCSS para estilos.

## Consecuencias
### Positivas
- Separación clara de responsabilidades: el frontend no conoce los detalles de base de datos y el backend no genera HTML de presentación.
- Capacidad de evolucionar o reemplazar clientes (p. ej., aplicaciones móviles futuras en React Native) reutilizando exactamente la misma API REST y canales WebSocket.
- Desarrollo ágil con recarga en caliente ultrarrápida (HMR) gracias a Vite.
- Tipado estricto extremo con contratos OpenAPI que evita errores de sincronización de datos entre cliente y servidor.

### Negativas / Retos
- Necesidad de gestionar CORS y autenticación basada en tokens sin compartir estado de sesión de servidor en memoria.
- Requiere coordinación de dos ciclos de construcción (`npm run build` y `python manage.py collectstatic`).
