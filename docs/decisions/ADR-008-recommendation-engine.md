# ADR-008: Motor de Recomendación Híbrido Multicriterio

## Estado
Aceptado

## Contexto
El descubrimiento de lecturas personalizadas es un pilar central de MyBookConnect. Para ofrecer sugerencias relevantes, la plataforma debe resolver el problema del inicio en frío (*cold-start*) para nuevos usuarios y al mismo tiempo afinar sugerencias para lectores veteranos con abundante historial de lecturas y valoraciones:
- Un enfoque puramente colaborativo (*collaborative filtering*) falla con usuarios y libros recién añadidos.
- Un enfoque basado únicamente en categorías (*content-based*) ignora la calidad subjetiva y las tendencias de la comunidad.

## Decisión
Implementar un motor de recomendación híbrido multietapa (`HybridRecommendationEngine`):
1. **Perfil de Afinidad del Usuario:**
   - Analizar los géneros y categorías de los libros mejor valorados (≥ 4 estrellas) o completados en la biblioteca del usuario.
2. **Ponderación Multicriterio:**
   - **Afinidad de Género / Autor:** Coincidencia con las preferencias históricas del lector.
   - **Popularidad y Calidad Ponderada:** Libros con promedio de calificación elevado y número significativo de reseñas comunitarias.
   - **Feedback Explícito:** Exclusión automática de libros ya leídos, descartados o marcados explícitamente como "no me interesa".
3. **Mecanismo de Respaldo (*Cold-Start*):**
   - Cuando el usuario es nuevo o no posee lecturas registradas, el motor recurre a una selección curada de libros destacados y obras aclamadas por la comunidad.
4. **Caché y Rendimiento:**
   - Resultados de recomendaciones precomputados o cacheados en Redis para evitar reevaluaciones costosas en cada visita al feed principal.

## Consecuencias
### Positivas
- Resuelve eficazmente el problema del cold-start tanto a nivel de usuario como de catálogo.
- Sugerencias variadas y precisas que combinan gustos personales comprobados con obras de alta reputación.
- Latencia de respuesta reducida mediante almacenamiento en caché Redis.

### Negativas / Retos
- Requiere monitorizar la diversidad de recomendaciones para evitar burbujas de filtro centradas exclusivamente en un único género.
