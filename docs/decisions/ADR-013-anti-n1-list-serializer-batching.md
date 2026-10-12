# ADR-013: Erradicación de Consultas N+1 en DRF mediante Batching en Nivel ListSerializer

## Estado
Aceptado

## Contexto
En los endpoints de listado de catálogo (`GET /api/v1/books/`), los campos calculados `rating_distribution` y `reviews_count` de `BookSerializer` ejecutaban consultas de agregación individuales en la base de datos por cada libro retornado por el paginador:
$$\text{Consultas} = 1 \text{ (listado)} + N \text{ (rating distribution)} + N \text{ (reviews count)} = 2N + 1$$
Para un listado típico de 20 libros, se disparaban 41 consultas SQL independientes, degradando severamente la latencia p95 bajo concurrencia moderada.

## Decisión
1. **Detección de Lote en el Serializador Padre:**
   - En `BookSerializer`, se inspecciona `self.parent`. Si `isinstance(self.parent, serializers.ListSerializer)` y posee `instance`, el serializador detecta que está operando sobre una colección.
2. **Batching Agregado en una Sola Consulta SQL:**
   - Se extraen todos los IDs de los libros de la página (`book_ids`).
   - Se ejecuta una única consulta con `Review.objects.filter(book_id__in=book_ids).values('book_id', 'rating').annotate(total=Count('id'))`.
3. **Memoización en el Ámbito del Request:**
   - Los resultados precalculados se almacenan en el objeto `request` (`request._cached_book_rating_dists` y `request._cached_book_review_counts`).
   - Cada llamada subsiguiente de un libro individual resuelve sus datos en memoria en tiempo $O(1)$ sin realizar ninguna consulta SQL adicional.
4. **Respeto a Serializadores Anidados:**
   - Si `BookSerializer` se usa de forma anidada individual (por ejemplo dentro de `ReviewSerializer`), no fuerza la iteración de objetos padre incompatibles, garantizando retrocompatibilidad y seguridad de tipos.

## Consecuencias
### Positivas
- Reducción drástica del número de consultas SQL en el catálogo de libros: de $2N + 1$ a una cantidad constante $O(1)$ fija (4 consultas en total con prefetch de autores y géneros).
- Disminución de la latencia del catálogo y mejora directa en los SLAs de concurrencia.
- Invariante comprobado mediante pruebas automatizadas con `CaptureQueriesContext`.

### Negativas / Retos
- Lógica de batching dependiente de la presencia del objeto `request` en el contexto del serializador.
