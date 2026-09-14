# ADR-007: Estrategia de Búsqueda Híbrida (Trigramas PostgreSQL + Búsqueda Semántica)

## Estado
Aceptado

## Contexto
Los usuarios de MyBookConnect necesitan encontrar libros, autores y géneros mediante búsquedas tolerantes a fallos tipográficos, búsquedas exactas por ISBN y consultas conceptuales o temáticas ("novelas distópicas sobre inteligencia artificial"):
- Los operadores `LIKE` o `ILIKE` en SQL estándar son lentos para grandes volúmenes y carecen de tolerancia a erratas (typos).
- Introducir Elasticsearch o Solr añade una gran sobrecarga operativa de infraestructura, sincronización y memoria.
- Se requiere una solución nativa de alto rendimiento en base de datos para búsqueda léxica combinada con capacidades modernas de búsqueda semántica asistida por IA.

## Decisión
Adoptar una arquitectura de búsqueda híbrida en dos niveles:
1. **Búsqueda Léxica y Fuzzy con PostgreSQL (`pg_trgm` + GIN Indexes):**
   - Habilitar la extensión nativa `pg_trgm` en PostgreSQL.
   - Crear índices invertidos GIN sobre campos clave (`title`, `author_name`, `summary`).
   - Aplicar similitud trigramática con umbral configurable (`similarity(title, %s) > 0.25`) para tolerar erratas frecuentes del usuario sin latencia apreciable.
2. **Búsqueda Semántica / Vectorial (AI Integration):**
   - Integrar un endpoint de búsqueda semántica (`/api/search/semantic/`) compatible con OpenAI o embeddings locales.
   - Consultar vectores de significado para resolver consultas naturales abstractas que no coinciden en palabras exactas con el título o sinopsis.

## Consecuencias
### Positivas
- Máxima eficiencia sin infraestructura adicional: PostgreSQL resuelve millones de consultas de búsqueda difusa en milisegundos mediante índices GIN.
- Experiencia de usuario excelente al tolerar erratas y errores ortográficos comunes.
- Extensibilidad semántica para descubrimientos ricos mediante embeddings sin comprometer la velocidad de la búsqueda básica.

### Negativas / Retos
- Los índices GIN consumen espacio en disco y aumentan ligeramente el tiempo de inserción y actualización de libros.
- La búsqueda semántica requiere una API key externa o un servicio de embeddings disponible.
