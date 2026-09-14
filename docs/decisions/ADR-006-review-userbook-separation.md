# ADR-006: Separación de Responsabilidades entre Review y UserBook

## Estado
Aceptado

## Contexto
En los modelos iniciales de la plataforma existía ambigüedad y duplicidad entre la pertenencia de un libro a la biblioteca de un usuario y la publicación de una reseña comunitaria:
- Un usuario puede querer registrar un libro en su estantería como "Leído" o "Leyendo" sin publicar una reseña comunitaria ni otorgar una puntuación pública.
- A la inversa, una reseña pública con texto y valoración no debe confundirse con los metadatos privados de lectura del usuario (página actual, fecha de inicio, formato digital/físico, notas personales).

## Decisión
Separar taxativamente el modelo en dos entidades independientes y complementarias:
1. **`UserBook` (Biblioteca Personal):**
   - Ámbito: Privado / configurable por el nivel de privacidad del lector.
   - Datos: Estado de lectura (`want_to_read`, `reading`, `read`, `abandoned`), progreso numérico (0 a 100), página actual, propiedad física, formato y notas personales.
2. **`Review` (Crítica y Reseña Pública):**
   - Ámbito: Público en la ficha del libro.
   - Datos: Calificación de 1 a 5 estrellas, texto argumentativo, votos de utilidad de otros lectores y aviso de spoilers.

## Consecuencias
### Positivas
- Claridad total en los modelos de datos y en las pantallas de la interfaz de usuario.
- Flexibilidad para que los lectores mantengan notas privadas sobre sus libros sin exponerlas en la página pública de reseñas.
- Consultas optimizadas con índices independientes para cada caso de uso.

### Negativas / Retos
- Requiere sincronización de sincronismos opcionales cuando un usuario reseña y califica una obra que también tiene en su biblioteca.
