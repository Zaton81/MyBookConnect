# Fase 25 — Embeddings, Persistencia Vectorial y Búsqueda Semántica

## 1. Visión y Arquitectura

La **Fase 25 — Embeddings y pgvector** consolida la canalización integral de búsqueda semántica y vectorización del catálogo, diseñada para escalar eficientemente de acuerdo con el [RoadmapV2.md](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/RoadmapV2.md):

```text
┌─────────────────┐
│      Book       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│     Content Normalization       │ -> Limpieza de HTML, normalización NFC,
│  (Hash SHA256 para idempotencia)│    composición estructurada (título, autor, géneros, sinopsis)
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│     Embedding Job (Celery)      │ -> Ejecución asíncrona sin bloquear peticiones HTTP
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Persistencia (BookEmbedding)   │ -> Tabla satélite con modelo, versión, dimensión y vector
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│        ANN Vector Search        │ -> Similitud coseno con aislamiento estricto de modelo
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│     Hybrid Search Ranking       │ -> Fusión ponderada: Textual (FTS) + Difusa (Trigram) + Vectorial
└─────────────────────────────────┘
```

---

## 2. Componentes Principales

### A. Normalización Formal de Contenido
- **Función:** `normalize_book_content_for_embedding(book: Book) -> tuple[str, str]`
- **Características:**
  - Limpieza de etiquetas HTML en sinopsis mediante expresiones regulares seguras.
  - Normalización canónica de caracteres Unicode (`unicodedata.normalize('NFC', ...)`).
  - Ordenación alfabética y deduplicación de categorías para garantizar determinismo absoluto.
  - Cálculo de huella criptográfica SHA256 (`content_hash`) que detecta cambios de contenido sin recalcular vectores innecesariamente si no hubo alteraciones.

### B. Tareas en Segundo Plano (Celery)
- **`generate_book_embedding_task(book_id: int, force: bool = False, model_name: str = None)`**:
  Vectoriza de manera asíncrona obras recién catalogadas o actualizadas, gobernando el ciclo de vida a través del modelo satélite `BookEmbedding`.
- **`batch_reindex_embeddings_task(batch_size: int = 50, force: bool = False, model_name: str = None)`**:
  Job de mantenimiento por lotes para indexación progresiva o periódica de obras pendientes o marcadas como `STALE`.

### C. Versionado y Aislamiento Estricto de Modelos
> **Regla de oro del Roadmap:** *"No mezclar embeddings de modelos incompatibles."*

El servicio `search_books_by_embedding` implementa un filtro estricto:
- Compara **únicamente** contra registros de `BookEmbedding` cuyo `embedding_model` coincida exactamente con el modelo que generó el vector de consulta (ej. `nomic-embed-text` o `text-embedding-3-small`).
- Comprueba que la longitud dimensional del vector coincida exactamente (`dimension == len(query_vector)`).
- Ignora cualquier vector de dimensión o modelo dispar para prevenir aberraciones matemáticas en el cálculo de similitud coseno.

### D. Observabilidad y Endpoints de API
1. **`GET /api/v1/books/ai/embeddings/stats/`**:
   - Total de libros en catálogo.
   - Total de embeddings completados, pendientes, fallidos y desactualizados (`STALE`).
   - Porcentaje de cobertura del catálogo (`coverage_percentage`).
   - Modelo activo configurado.
   - Desglose por modelo, versión y dimensión.
2. **`POST /api/v1/books/<pk>/ai/embeddings/generate/`**:
   - Generación o re-embedding bajo demanda con soporte para ejecución síncrona o encolado asíncrono (`async_mode: true`).

### E. Comando CLI de Gestión
- `python manage.py reindex_embeddings [--force] [--check-stale] [--batch-size=50] [--model=nomic-embed-text]`

---

## 3. Garantías de Calidad y Pruebas

- **Suite de Pruebas de la Fase 25 ([backend/tests/test_phase25_embeddings_pgvector.py](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/backend/tests/test_phase25_embeddings_pgvector.py)):**
  10 tests unitarios y de integración pasando al 100%:
  - Normalización y determinismo de hash SHA256.
  - Generación, persistencia e idempotencia de vector.
  - Aislamiento contra modelos y dimensiones incompatibles.
  - Tareas Celery de generación individual y por lotes.
  - Endpoints de observabilidad y vectorización bajo demanda.
- **Suite de Regresión Backend:**
  35 tests pasando sin fallos (`test_phase24_product_ai.py`, `test_phase26_ai.py`, `test_phase06_search_ranking.py`).
- **Frontend Code Quality:**
  100% limpio en formateo (`pnpm format:check`), tipado (`pnpm typecheck`) y 27 tests pasando en Vitest (`pnpm test`).
