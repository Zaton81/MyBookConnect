# Inteligencia Artificial y Búsqueda Avanzada

## 1. Motor de Búsqueda Unificado (`UnifiedSearchEngine`)

El motor de búsqueda de MyBookConnect integra una arquitectura multicanal unificada (`backend/books/services/unified_search_service.py`) que combina tres canales complementarios de recuperación y un modelo de puntuación fusionado:

### Canales de Búsqueda
1. **Canal Textual (PostgreSQL Full-Text Search - FTS):**
   - Configuración léxica en idioma español (`config='spanish'`).
   - Ponderación de vectores: Título (peso A), ISBN (peso A), Autor (peso B), Categorías (peso B), Descripción (peso C).
   - Generación de `SearchRank` y normalización a escala $[0, 1]$.

2. **Canal Difuso por Trigramas (`pg_trgm`):**
   - Utiliza la extensión `pg_trgm` sobre los campos `Book.title`, `Book.description` y `Author.name`.
   - Índices GIN dedicados (`idx_book_title_trgm`, `idx_book_desc_trgm`, `idx_author_name_trgm`).
   - Cálculo combinado mediante `Greatest(TrigramSimilarity, TrigramWordSimilarity)` para tolerancia extrema a erratas tipográficas ("soledd" $\rightarrow$ "soledad", "Cortzar" $\rightarrow$ "Cortázar").

3. **Canal Semántico (Vector Embeddings y Expansión Conceptual):**
   - Almacenamiento vectorial en `Book.embedding` (`JSONField`).
   - Cálculo de similitud coseno vectorial directa (`ai.embeddings.cosine_similarity`) sobre embeddings precalculados mediante Celery (`generate_book_embedding_task`).
   - Fallback semántico a expansión temática contextual (`ai.services.semantic_search_books`).

### Fusión y Re-ranking Multicanal
La puntuación unificada combina los pesos según el modo seleccionado:
- **Modo Híbrido (`hybrid`):** $S_{\text{unified}} = (0.45 \cdot S_{\text{text}}) + (0.30 \cdot S_{\text{fuzzy}}) + (0.25 \cdot S_{\text{semantic}}) + \text{boost}_{\text{rating}}$
- **Modos Específicos:** `text` ($100\%$ textual), `fuzzy` ($100\%$ difuso), `semantic` ($100\%$ semántico).
- **Clasificación de Coincidencia (`match_type`):** `exact`, `fuzzy`, `semantic` o `hybrid`.
- **Filtros Soportados:** Categoría (por slug, ID o nombre), Autor (por ID, nombre o trigramas), Calificación promedio mínima (`min_rating`).

### Endpoints Disponibles
- **Endpoint Dedicado:** `GET /api/v1/books/search/?q=...&mode=...&category=...&author=...&min_rating=...&page=1&page_size=20`
  Retorna el desglose de puntuaciones (`scores.text_score`, `scores.fuzzy_score`, `scores.semantic_score`), `unified_score` y `match_type`.
- **Compatibilidad Retroactiva:** `GET /api/v1/books/?q=...` y `GET /api/v1/books/?search=...` delegan internamente a `UnifiedSearchEngine(mode='hybrid')` preservando el orden del ranking.

---

## 2. Subsistema de Inteligencia Artificial (`backend/ai/`)

### Diseño Desacoplado y Compatible con OpenAI
El cliente de IA está diseñado como un adaptador desacoplado que puede utilizar modelos comerciales (OpenAI GPT-4o / GPT-3.5) o instancias locales compatibles (vLLM, Ollama) configurando `OPENAI_API_BASE` y `OPENAI_API_KEY`.

### Funcionalidades Implementadas
1. **Resúmenes Contextuales (`AIBookSummaryView`):** Genera sinopsis breves, listas de temas clave y perfiles de público objetivo a partir de los metadatos del libro.
2. **Búsqueda Semántica (`AISemanticSearchView`):** Permite encontrar libros describiendo tramas o sensaciones ("novela nostálgica ambientada en la lluvia") mediante cálculo de similitud sobre representaciones vectoriales.
3. **Herramientas de Agente (`AIToolExecuteView`):** Capacita al asistente para consultar disponibilidad, estadísticas o autores mediante llamadas a funciones estrictamente tipadas.

### Seguridad y Mitigación de Prompt Injection
- `PromptSecurityService`: Analiza cada entrada del usuario con expresiones regulares y patrones heurísticos para neutralizar intentos de manipulación del sistema prompt ("ignore previous instructions", "act as root", "jailbreak").
- Limitación estricta de longitud y validación de esquemas JSON en respuestas estructuradas.
