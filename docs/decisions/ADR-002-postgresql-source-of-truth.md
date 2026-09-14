# ADR-002: PostgreSQL como Fuente Única de Verdad

## Estado
Aceptado

## Contexto
En una red social de lectura, la consistencia y la integridad de los datos son críticas:
- No deben existir libros duplicados para un mismo usuario en su estantería.
- Las puntuaciones deben estar estrictamente acotadas entre 1 y 5.
- Los seguimientos y bloqueos deben prevenir duplicidades o inconsistencias bidireccionales.
- Se requiere capacidad de búsqueda difusa sin introducir la complejidad operativa de un clúster de Elasticsearch en etapas tempranas.

## Decisión
Establecer **PostgreSQL 16** como la única fuente de verdad (*single source of truth*) de la plataforma:
1. Toda restricción de negocio se impone en la capa de base de datos (`unique_together`, `CheckConstraint`, `ForeignKey` con políticas `CASCADE`/`SET_NULL`).
2. Activación de la extensión `pg_trgm` para índices de similitud de trigramas (`GinIndex`) sobre títulos, descripciones y nombres de autores.
3. Transacciones atómicas con aislamiento ACID para operaciones compuestas (p. ej., actualización de progreso e inserción en el feed de actividad).

## Consecuencias
### Positivas
- Prevención total de datos corruptos o huérfanos a nivel de motor de almacenamiento.
- Excelente rendimiento en búsquedas difusas con latencias sub-milisegundo sin requerir servicios adicionales.
- Migraciones seguras y reproducibles con Django ORM.

### Negativas / Retos
- Para pruebas automatizadas de integridad con errores esperados, se deben usar bloques `transaction.atomic()` para evitar abortos de sesión en PostgreSQL.
