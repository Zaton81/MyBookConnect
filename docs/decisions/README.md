# Architecture Decision Records (ADRs) — My Book Social

Este directorio documenta todas las Decisiones Arquitectónicas (ADRs) adoptadas a lo largo de la evolución de **My Book Social**. Cada registro describe el contexto, la decisión técnica adoptada y sus consecuencias prácticas.

---

## Índice de Decisiones Arquitectónicas

| Identificador | Título | Estado | Fecha / Hito |
| :--- | :--- | :---: | :--- |
| [ADR-001](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-001-django-react.md) | Arquitectura desacoplada Django REST Framework y React SPA | Aceptado | Fase Inicial |
| [ADR-002](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-002-postgresql-source-of-truth.md) | PostgreSQL como Fuente Única de Verdad Transaccional y Relacional | Aceptado | Fase Inicial |
| [ADR-003](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-003-redis-caching-and-channels.md) | Redis como Capa de Caché y Canal de Mensajería para WebSockets | Aceptado | Fase Inicial |
| [ADR-004](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-004-celery-async-workers.md) | Celery para Tareas en Segundo Plano y Procesamiento Asíncrono | Aceptado | Fase Inicial |
| [ADR-005](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-005-jwt-security-strategy.md) | Estrategia de Autenticación y Seguridad con JWT | Aceptado | Fase Inicial |
| [ADR-006](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-006-review-userbook-separation.md) | Separación Arquitectónica de Modelos `Review` y `UserBook` | Aceptado | Fase Inicial |
| [ADR-007](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-007-search-and-trigrams.md) | Búsqueda Avanzada Híbrida con Índices Trigram (pg_trgm) y Full-Text Search | Aceptado | Fase Inicial |
| [ADR-008](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-008-recommendation-engine.md) | Motor de Recomendación Híbrido Basado en Contenido y Filtrado Colaborativo | Aceptado | Fase Inicial |
| [ADR-009](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-009-secure-cookie-jwt-and-ws-tickets.md) | Mitigación de XSS mediante Cookies HttpOnly y Handshake WebSocket por Tickets Efímeros | Aceptado | Fase A2 |
| [ADR-010](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-010-isolated-production-docker-topology.md) | Topología de Contenedores de Producción Aislada y Nginx como Punto Único de Entrada | Aceptado | Fase B1 |
| [ADR-011](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-011-disaster-recovery-and-encrypted-backups.md) | Estrategia de Copias de Seguridad Cifradas AES-256, DRP y Verificación de Integridad | Aceptado | Fase B2 |
| [ADR-012](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-012-celery-multi-queue-and-db-read-replicas.md) | Enrutamiento Celery Multi-Cola y Arquitectura de Réplicas de Lectura en Base de Datos | Aceptado | Fase B4 |
| [ADR-013](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/ADR-013-anti-n1-list-serializer-batching.md) | Erradicación de Consultas N+1 en DRF mediante Batching en Nivel ListSerializer | Aceptado | Fase C1 |

---

## Criterios para Crear o Modificar un ADR
1. **Inmutabilidad de Contexto Histórico:** Un ADR aceptado no se borra. Si una decisión cambia, se crea un nuevo ADR que referencia y reemplaza (supersedes) al anterior.
2. **Estructura Requerida:** Todo ADR debe contener: Título, Estado, Contexto, Decisión y Consecuencias (Positivas y Negativas/Retos).
3. **Aprobación Formal:** Toda decisión que altere modelos de datos, protocolos de seguridad o topología de producción debe consensuarse y aprobarse mediante Pull Request.
