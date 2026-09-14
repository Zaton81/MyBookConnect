# Inteligencia Artificial y Búsqueda Avanzada

## 1. Búsqueda Híbrida en el Catálogo

El motor de búsqueda de MyBookConnect combina dos técnicas complementarias:

### Búsqueda Difusa por Trigramas en PostgreSQL
- Emplea la extensión `pg_trgm` sobre los campos de título, autor y sinopsis.
- Cuenta con índices GIN dedicados:
  - `idx_book_title_trgm` en `Book.title`.
  - `idx_book_desc_trgm` en `Book.description`.
  - `idx_author_name_trgm` en `Author.name`.
- Permite tolerancia a errores tipográficos y coincidencias parciales con latencias en base de datos inferiores a $1\text{ ms}$.

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
