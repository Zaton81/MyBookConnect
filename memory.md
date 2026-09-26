# Memoria del Proyecto y Contexto Operativo — MyBookConnect

Este documento contiene el **contexto arquitectónico continuo**, el **historial de decisiones técnicas**, las **restricciones obligatorias** y las **trampas resueltas (*gotchas*)** del proyecto **MyBookConnect**.

Cualquier agente de IA o desarrollador que se incorpore a la base de código **DEBE leer y respetar este documento** antes de realizar cambios.

---

## 1. Reglas de Oro del Proyecto (Invariantes Obligatorias)

1. **Rama de trabajo exclusiva:**
   - Todo el trabajo de desarrollo e integración se realiza **SIEMPRE en la rama `develop`**.
   - Nunca hacer push directo a `main`.
2. **Flujo de Fases y Commits:**
   - Seguir estrictamente el orden de fases definido en [RoadmapV2.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV2.md).
   - Redactar y someter a aprobación del usuario un plan detallado en `implementation_plan.md` antes de implementar una nueva fase.
   - Tras completar cada fase, verificar calidad (100% tests pasando, linters limpios, cero cambios de migración pendientes) y realizar inmediatamente un **commit semántico** y **`git push origin develop`**.
3. **Cero Regresiones:**
   - La suite completa de backend (114 tests del Roadmap, >680 tests totales) y frontend (27 tests de Vitest) debe pasar al 100%. Ningún commit debe romper funcionalidad previa.
4. **Seguridad de Base de Datos de Pruebas:**
   - **PROHIBIDO ejecutar comandos concurrentes/paralelos de `pytest`**. La base de datos de test PostgreSQL (`test_booksocial`) entra en bloqueo transaccional (`OperationalError: database is being accessed by other users`) si se ejecutan múltiples instancias a la vez.

---

## 2. Pila Tecnológica y Arquitectura

- **Backend:** Python 3.12, Django 5.2, Django REST Framework, Django Channels (Daphne ASGI), Celery.
- **Bases de Datos y Caché:** PostgreSQL 16 con extensión `pgvector`, Redis 7 Alpine (caché L2, rate limiting, broker de Celery y layer de Channels).
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS, Zustand (gestión de estado de autenticación y UI), React Query (@tanstack/react-query).
- **Contenedores y Producción:** Docker Compose, Nginx 1.27-alpine como API Gateway / Reverse Proxy, multi-stage Dockerfiles, redes aisladas (`frontend_net` y `backend_net internal: true`).

---

## 3. Estado de Ejecución del Roadmap (RoadmapV2.md)

| Fase | Título | Estado | Hito Clave / Entregable |
| :--- | :--- | :--- | :--- |
| **01** | Integridad del Dominio | COMPLETADA | Constraints en modelos, slugging, normalización ISBN y soft-deletes. |
| **02** | Privacidad Social y Bloqueos | COMPLETADA | Políticas de visibilidad de perfiles, bloqueos bidireccionales (retorno 404/403). |
| **03** | Auth y Seguridad de Sesiones | COMPLETADA | JWT con rotación, blacklist, control de sesiones concurrentes y confirmación de email. |
| **04** | Mensajería Realtime | COMPLETADA | WebSockets seguros con Daphne, Channels y Redis channel layer. |
| **05** | IA y Seguridad | COMPLETADA | Multi-proveedor (OpenAI, OpenRouter, Ollama), guardrails contra prompt injection y sanitización. |
| **06** | Búsqueda y Ranking | COMPLETADA | Búsqueda híbrida unificada: trigram (`pg_trgm`), vector embeddings y metadatos. |
| **07** | Recomendaciones | COMPLETADA | Motor v3 ponderado con embeddings semánticos, similitud coseno y feedback loop. |
| **08** | Estrategia de Caché | COMPLETADA | Invalidación en cascada, `safe_cache_get/set` con fallback graceful ante fallos de Redis. |
| **09** | Rendimiento y Presupuestos | COMPLETADA | Erradicación de N+1, índices compuestos (`Book`, `Review`, `UserBook`) y SLAs p95/p99. |
| **10** | Calidad de Frontend | COMPLETADA | ESLint, Prettier, TypeScript strict, Vitest, auto scroll-to-top en navegación. |
| **11** | Backend Testing Suite | COMPLETADA | Tests Unit, Integration, API, Security (IDOR, auth 401, injection) y Regression. |
| **12** | CI/CD Pipelines | COMPLETADA | GitHub Actions modulares (`ci-backend`, `ci-frontend`, `ci-docker`, `security`, `dependabot`). |
| **13** | Docker y Producción | COMPLETADA | Nginx reverse proxy, aislamiento de redes, sondas `/health/live` y `/health/ready`, graceful shutdown. |
| **14** | **Observabilidad (EN CURSO)** | **SIGUIENTE** | Formato JSON estructurado sin PII/tokens, métricas de backend y KPIs de producto (DAU/WAU/MAU). |

---

## 4. Trampas Conocidas y Lecciones Aprendidas (Gotchas)

### 4.1. Token de Autenticación en Frontend
- **Problema histórico:** Varios componentes de gamificación buscaban el token con `localStorage.getItem('access_token')`, devolviendo `null` porque Zustand almacena el estado bajo la clave `auth-storage`.
- **Solución Canónica:** Importar siempre el hook central:
  ```typescript
  import { useAuthStore } from '@/store/auth';
  const token = useAuthStore((state) => state.token);
  ```

### 4.2. Bloqueos Sociales y Visibilidad de Perfil
- Cuando el usuario Alice bloquea a Bob (o existe bloqueo mutuo), la política estricta de seguridad ([backend/users/views.py](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/users/views.py)) devuelve **`404 NOT FOUND`** ("Usuario no encontrado") para no filtrar la existencia de la cuenta al acosador/bloqueado. En pruebas de acceso, esperar `status.HTTP_404_NOT_FOUND` o `status.HTTP_403_FORBIDDEN`.

### 4.3. Importación CSV de Goodreads
- El servicio [CSVImportService](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/books/services/csv_import_service.py) devuelve un payload estructurado compatible tanto con `preview_items` como con `raw_items_payload`.
- El componente `ImportBooksModal.tsx` tolera ambas claves:
  ```typescript
  const items = previewData?.raw_items_payload || previewData?.preview_items || [];
  ```

### 4.4. Aislamiento de Embeddings en Entorno de Pruebas
- Si se ejecutan pruebas de búsqueda que usan `mode='hybrid'`, asegurarse de mockear `OllamaProvider.get_embedding` y `get_embedding_for_text`:
  ```python
  with patch('ai.clients.ollama_client.OllamaProvider.get_embedding', return_value=None), \
       patch('ai.embeddings.get_embedding_for_text', return_value=None):
      # Petición de búsqueda sin demoras de red contra Ollama inexistente en tests
  ```

### 4.5. Sondas de Salud Desacopladas
- `/health/live`: Sonda de Liveness para orquestadores. **Nunca debe conectar a la base de datos ni a Redis**; comprueba solo el proceso Django/Daphne.
- `/health/ready`: Sonda de Readiness. Comprueba conectividad con PostgreSQL y Redis, retornando `503` ante cualquier fallo.

---

## 5. Ubicación de Documentación Relevante

- **Arquitectura y Rendimiento:** [docs/architecture/database_performance.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/architecture/database_performance.md)
- **Estrategia de Pruebas Backend:** [docs/backend/testing_strategy.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/backend/testing_strategy.md)
- **Calidad de Frontend:** [docs/frontend/quality_and_testing.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/frontend/quality_and_testing.md)
- **CI/CD Pipeline:** [docs/devops/ci_cd_pipeline.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/ci_cd_pipeline.md)
- **Despliegue y Docker en Producción:** [docs/devops/production_docker.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/devops/production_docker.md)
- **Scripts de Copias de Seguridad:** `scripts/backup/backup_db.sh` y `scripts/backup/restore_db.sh`
