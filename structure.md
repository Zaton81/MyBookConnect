# Estructura del Proyecto MyBookConnect

Mapa completo y actualizado de la organización de directorios, aplicaciones, módulos y pruebas en el monorepositorio de **MyBookConnect**.

---

## 1. Raíz del Repositorio

```text
MyBookConnect/
├── .github/                   # Flujos de trabajo de CI/CD (GitHub Actions)
├── backend/                   # Proyecto backend en Django 5.2 LTS y Celery
├── frontend/                  # Aplicación cliente SPA en React 18, Vite y TypeScript
├── docs/                      # Documentación técnica modular y ADRs
├── scripts/                   # Arneses de prueba de carga (Locust, k6)
├── backups/                   # Utilidades de respaldo y persistencia de datos
├── docker-compose.yml         # Orquestación de desarrollo local con Docker
├── docker-compose.prod.yml    # Orquestación de producción con aislamiento de redes
├── architecture.md            # Diagramas y diseño de arquitectura
├── structure.md               # Este documento de estructura de directorios
├── README.md                  # Documentación principal y guía de inicio rápido
├── Roadmap.md                 # Hoja de ruta exhaustiva del proyecto (50 fases)
└── instruccionesAgente.md     # Directrices y principios de ingeniería de software
```

---

## 2. Backend (`/backend`)

El backend está organizado en aplicaciones Django modulares según su dominio de negocio:

```text
backend/
├── ai/                                # Módulo de Inteligencia Artificial contextual
│   ├── client.py                      # Cliente HTTP compatible con OpenAI
│   ├── prompt_security.py             # Detección y mitigación de prompt injection
│   ├── semantic_search.py             # Motor de búsqueda semántica con embeddings
│   ├── services.py                    # Generación de resúmenes y análisis
│   └── tools.py                       # Herramientas ejecutables por el agente
├── books/                             # Dominio principal: Catálogo, Biblioteca, Reseñas
│   ├── management/commands/           # Comandos de administración de Django
│   │   └── benchmark_queries.py       # Perfilado de consultas con EXPLAIN ANALYZE
│   ├── services/                      # Lógica de dominio desacoplada
│   │   ├── providers/                 # Proveedores de metadatos externos
│   │   │   ├── google_books.py        # Integración con API Google Books v1
│   │   │   ├── openlibrary.py         # Integración con APIs de OpenLibrary
│   │   │   └── wikipedia.py           # Búsqueda de obras y autores en Wikipedia
│   │   ├── cover_service.py           # Descarga y optimización de carátulas
│   │   ├── enrichment_service.py      # Orquestador de enriquecimiento de libros
│   │   ├── recommendation_service.py  # Algoritmo de recomendaciones híbridas
│   │   └── stats_service.py           # Cálculo de estadísticas de lectura
│   ├── admin.py                       # Panel de administración de Django
│   ├── admin_views.py                 # Vistas administrativas y documentos legales
│   ├── cache_utils.py                 # Claves centralizadas e invalidación de Redis
│   ├── media_utils.py                 # Validación de portadas e imágenes
│   ├── models.py                      # Modelos: Book, Author, Category, UserBook, Review
│   ├── serializers.py                 # Serializadores DRF con validaciones
│   ├── tasks.py                       # Tareas asíncronas de Celery
│   ├── urls.py                        # Enrutamiento de la API de libros
│   └── views.py                       # Controladores REST del catálogo y biblioteca
├── users/                             # Gestión de usuarios, perfiles y seguridad
│   ├── models.py                      # CustomUser, Follow, Block, UserActivity
│   ├── serializers.py                 # Serializadores de perfil y autenticación
│   ├── views.py                       # Vistas de registro, login y perfil
│   ├── permissions.py                 # Permisos personalizados (privacidad, autoría)
│   └── urls.py                        # Enrutamiento de /api/v1/users/ y /auth/
├── messages_app/                      # Mensajería instantánea y chats
│   ├── consumers.py                   # WebSocket Consumers (ChatConsumer)
│   ├── middleware.py                  # Autenticación JWT para WebSockets
│   ├── models.py                      # Conversation, Message
│   ├── routing.py                     # Enrutamiento de canales WebSocket
│   └── views.py                       # API REST para historial de conversaciones
├── mybookconnect/                     # Configuración principal del proyecto Django
│   ├── asgi.py                        # Entrada ASGI para Daphne (WebSockets)
│   ├── celery.py                      # Configuración del broker y workers de Celery
│   ├── logging_formatters.py          # Formateador JSON estructurado sin acoplamientos
│   ├── observability.py               # Middleware de trazabilidad y métricas
│   ├── query_profiler.py              # Perfilador de consultas PostgreSQL EXPLAIN
│   ├── settings.py                    # Ajustes de entorno, base de datos y plugins
│   ├── urls.py                        # Enrutador principal de URLs del sistema
│   └── wsgi.py                        # Entrada WSGI para Gunicorn (HTTP)
├── tests/                             # Suite de pruebas automatizadas del backend
│   ├── test_admin_api.py              # Pruebas de endpoints de administración
│   ├── test_auth_security.py          # Pruebas de autenticación JWT y blacklist
│   ├── test_caching.py                # Pruebas de caché en Redis e invalidación
│   ├── test_celery_tasks.py           # Pruebas de tareas asíncronas
│   ├── test_chat_websockets.py        # Pruebas de WebSockets y canales de chat
│   ├── test_database_performance.py   # Pruebas de consultas N+1 e índices
│   ├── test_domain_models.py          # Pruebas de integridad de modelos
│   ├── test_phase40_backend_testing.py# Pruebas de consolidación de backend
│   ├── test_phase41_postgres_redis.py # Pruebas de integración con PG y Redis
│   ├── test_phase42_observability.py  # Pruebas de logging JSON y métricas
│   ├── test_phase43_performance.py    # Pruebas de SLAs y benchmarks de latencia
│   └── ...                            # Cobertura completa de fases anteriores
├── Dockerfile                         # Imagen Docker del backend
├── pytest.ini                         # Configuración del ejecutor de tests Pytest
└── requirements.txt                   # Dependencias fijadas del backend
```

---

## 3. Frontend (`/frontend`)

El frontend está estructurado mediante una arquitectura basada en características (*feature-based architecture*):

```text
frontend/
├── src/
│   ├── assets/                # Logotipos, imágenes y recursos estáticos
│   ├── components/            # Componentes reutilizables compartidos
│   │   ├── common/            # Modales, spinners, banners (CookieBanner, etc.)
│   │   ├── forms/             # Controles de formulario validados con Zod
│   │   └── layout/            # Navbar, Footer, Sidebar, Logo
│   ├── features/              # Módulos por dominio funcional
│   │   ├── admin/             # Panel de administración frontend
│   │   ├── ai/                # Chatbot literario y asistentes de IA
│   │   ├── auth/              # Formularios de Login, Registro y Recuperación
│   │   ├── books/             # Catálogo, Detalle de libro, Formularios de alta
│   │   ├── library/           # Biblioteca personal, estados de lectura, filtros
│   │   ├── social/            # Feed social, lista de amigos y chats
│   │   └── legal/             # Documentos legales (Privacidad, Términos, Cookies)
│   ├── store/                 # Gestión de estado global con Zustand
│   │   ├── auth.ts            # Estado de sesión y tokens JWT del usuario
│   │   └── theme.ts           # Modo claro / oscuro persistido
│   ├── test/                  # Configuración y utilidades de testing
│   │   └── setup.ts           # Configuración de Vitest y JSDOM
│   ├── types/                 # Definición de tipos TypeScript
│   │   └── api.ts             # Tipos generados a partir de OpenAPI / Swagger
│   ├── utils/                 # Utilidades auxiliares (fechas, urls de medios)
│   ├── App.tsx                # Árbol de enrutamiento principal con React Router
│   ├── index.css              # Estilos globales de TailwindCSS y temas
│   └── main.tsx               # Punto de entrada de la aplicación React
├── package.json               # Dependencias del frontend y scripts npm
├── tailwind.config.js         # Configuración de TailwindCSS y tema Flowbite
├── tsconfig.json              # Configuración del compilador TypeScript estricto
├── vite.config.ts             # Configuración del servidor de desarrollo y empaquetador
└── vitest.config.ts           # Configuración del ejecutor de pruebas Vitest
```

---

## 4. Scripts y Utilidades (`/scripts`)

```text
scripts/
├── locustfile.py              # Prueba de carga concurrente con Locust
└── k6_load_test.js            # Prueba de rendimiento y umbrales con k6
```
