# Arquitectura del Motor de Búsqueda Multicanal y Semántica (Fase 6)

## 1. Visión General

El sistema de búsqueda de MyBookConnect combina técnicas tradicionales de recuperación textual ponderada (Full-Text Search y Trigram Fuzzy Matching en PostgreSQL) con capacidades de búsqueda vectorial semántica mediante el modelo satélite `BookEmbedding`.

El objetivo principal es ofrecer una jerarquía estricta de precisión y relevancia donde:
1. Las coincidencias exactas y de prefijo tienen máxima prioridad.
2. La similitud trigram (`pg_trgm`) rescata errores tipográficos leves.
3. La similitud vectorial semántica resuelve consultas conceptuales y temáticas complejas.
4. Las métricas de popularidad y valoración (`average_rating`, `ratings_count`) solo actúan como desempate moderado ($\le 0.12$), impidiendo que libros populares eclipsen resultados contextualmente irrelevantes.
5. La paginación es 100% determinista y estable mediante ordenamiento estricto por `(-unified_score, -book.id)`.

---

## 2. Modelo de Datos Satélite: `BookEmbedding`

Para aislar el almacenamiento de vectores de alta dimensionalidad de las consultas transaccionales de la tabla `books_book`, se emplea el modelo satélite:

```python
class BookEmbedding(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="embedding")
    vector = models.JSONField(help_text="Vector embedding normalizado")
    dimension = models.PositiveIntegerField(default=1536)
    embedding_model = models.CharField(max_length=100, default="text-embedding-3-small")
    embedding_version = models.PositiveIntegerField(default=1)
    embedded_at = models.DateTimeField(default=timezone.now)
    embedding_status = models.CharField(max_length=20, choices=EmbeddingStatus.choices, default=EmbeddingStatus.CURRENT)
    content_hash = models.CharField(max_length=64, blank=True, help_text="SHA256 del contenido indexado")
```

### Ciclo de Vida y Detección de Cambios (`content_hash`)
- **Cálculo de Hash:** `compute_book_content_hash(book)` calcula el digest SHA-256 de:
  `f"{title}|{author}|{synopsis}|{categories}"`.
- **Detección de Desactualización:** `mark_stale_embeddings()` compara el hash actual del libro con el `content_hash` registrado en `BookEmbedding`. Si difieren, el estado transiciona a `STALE`.
- **Comando de Gestión:** `python manage.py reindex_embeddings` permite recalcular por lotes (`--batch-size`, `--force`, `--check-stale`, `--model`).

---

## 3. Jerarquía y Ponderación del Motor Unificado

La función `_blend_and_rank` en `UnifiedSearchEngine` calcula la puntuación unificada combinando los diferentes canales:

$$S_{\text{unified}} = w_{\text{text}} \cdot S_{\text{text}} + w_{\text{fuzzy}} \cdot S_{\text{fuzzy}} + w_{\text{sem}} \cdot S_{\text{semantic}} + w_{\text{pop}} \cdot S_{\text{pop}} + B_{\text{exact}}$$

### Ponderaciones por Modo:

| Canal / Factor | Modo `hybrid` | Modo `text` | Modo `semantic` |
| :--- | :--- | :--- | :--- |
| **Exact Match Bonus ($B_{\text{exact}}$)** | $+0.40$ (si título exacto) / $+0.25$ (si prefijo) | $+0.40$ / $+0.25$ | $+0.20$ |
| **Ponderación Textual ($w_{\text{text}}$)** | $0.40$ | $0.80$ | $0.10$ |
| **Ponderación Trigram Fuzzy ($w_{\text{fuzzy}}$)** | $0.20$ | $0.15$ | $0.05$ |
| **Ponderación Semántica ($w_{\text{sem}}$)** | $0.30$ | $0.00$ | $0.75$ |
| **Popularidad / Rating ($w_{\text{pop}}$)** | Máx. $0.10$ | Máx. $0.05$ | Máx. $0.10$ |

> **Garantía Anti-Eclipsamiento:** Ningún libro con baja similitud semántica o textual puede superar a un resultado relevante solo por su volumen de lecturas o rating elevado.

---

## 4. Tipos de Coincidencia (`match_type`)

Cada resultado incluye su clasificación de coincidencia:
- `exact`: Coincidencia exacta o por prefijo directo en el título.
- `text`: Coincidencia en búsqueda de texto completo PostgreSQL (`SearchVector`, `SearchRank`).
- `fuzzy`: Coincidencia trigram por similitud de caracteres (`pg_trgm`).
- `semantic`: Coincidencia vectorial mediante similitud coseno con embeddings vigentes.
- `hybrid`: Coincidencia con aporte significativo en múltiples canales (e.g. texto y semántica simultáneos).

---

## 5. Paginación Determinista y Desempate

En ordenamientos basados en puntuaciones flotantes (relevance score), empates exactos pueden provocar duplicados o ausencias de libros entre páginas sucesivas.
Para garantizar determinismo absoluto:
- Los resultados se ordenan estrictamente por la tupla: `(score, -book.id)`.
- En caso de idéntico `score`, el desempate es determinista por el identificador del libro.
