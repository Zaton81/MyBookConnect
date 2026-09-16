# Arquitectura del Sistema de Recomendaciones

## 1. Visión General

El sistema de recomendaciones de MyBookConnect está diseñado para proporcionar descubrimientos personalizados y relevantes a los lectores. Su evolución está estructurada en fases progresivas dentro del Roadmap de la plataforma:

- **Fase 49 (v1):** Algoritmo inicial determinista y explicable basado en la suma ponderada de 5 variables canónicas (género, autor, rating, historial, wishlist).
- **Fase 50 (v2):** Filtrado colaborativo basado en usuarios con gustos similares (*user-user similarity*).
- **Fase 51 (v3):** Embeddings vectoriales y similitud semántica profunda (*book embeddings*).

---

## 2. Motor de Recomendaciones v1 (`RecommendationEngineV1`)

El motor v1 (`backend/books/services/recommendation_v1_service.py`) no recurre a cajas negras ni a machine learning complejo. Opera mediante una suma ponderada normalizada de variables canónicas directamente extraídas de la interacción del usuario:

### Variables Canónicas

1. **Género ($S_{\text{genre}} \in [0, 1]$):**
   - Evalúa la afinidad del lector hacia las categorías literarias.
   - Pondera según el estado del libro (`READ`, `READING`, `WANT_TO_READ`) y la calificación otorgada (libros calificados con 4 o 5 estrellas aportan mayor peso).
   - $S_{\text{genre}} = \max_{c \in \text{book.categories}} \text{profile.category\_affinity}[c]$.

2. **Autor ($S_{\text{author}} \in [0, 1]$):**
   - Evalúa la fidelidad hacia autores ya leídos o altamente valorados por el lector.
   - $S_{\text{author}} = \text{profile.author\_affinity}[\text{book.author\_id}]$.

3. **Rating ($S_{\text{rating}} \in [0, 1]$):**
   - Señal comunitaria de calidad normalizada:
     $$S_{\text{rating}} = \min\left(1.0, \max\left(0.0, \frac{\text{average\_rating} - 3.0}{2.0}\right)\right)$$

4. **Historial ($S_{\text{history}} \in [0, 1]$):**
   - Mide la madurez lectora del usuario (volumen de libros leídos y en curso) y refuerza a candidatos que encajan con su trayectoria sin provocar saturación.

5. **Wishlist ($S_{\text{wishlist}} \in [0, 1]$):**
   - Refleja la intención de lectura próxima del usuario basada en obras añadidas a `WANT_TO_READ` o listas de deseos personalizadas.

### Fórmula de Ponderación Canónica v1

$$S_{\text{total}} = (w_{\text{genre}} \cdot S_{\text{genre}}) + (w_{\text{author}} \cdot S_{\text{author}}) + (w_{\text{rating}} \cdot S_{\text{rating}}) + (w_{\text{history}} \cdot S_{\text{history}}) + (w_{\text{wishlist}} \cdot S_{\text{wishlist}})$$

**Pesos por defecto:**
- $w_{\text{genre}} = 0.30$
- $w_{\text{author}} = 0.25$
- $w_{\text{rating}} = 0.15$
- $w_{\text{history}} = 0.15$
- $w_{\text{wishlist}} = 0.15$

---

## 3. Explicabilidad Transparente (*Explainability*)

Cada recomendación devuelta incluye:
- `score`: Puntuación final entre $0.0$ y $1.0$.
- `algorithm_version`: `"v1"`.
- `breakdown`: Puntuación desagregada por cada una de las 5 variables (`genre`, `author`, `rating`, `history`, `wishlist`).
- `reason`: Motivo explicativo generado en función de la variable con mayor contribución ponderada:
  - Autor dominante: *"Porque te gusta la obra de {autor}"*
  - Wishlist dominante: *"Alineado con los libros pendientes en tu lista de deseos"*
  - Género dominante: *"Basado en tu interés por {género}"*
  - Calificación comunitaria: *"Obra destacada y aclamada por la comunidad ({rating} ★)"*

---

## 4. Exclusión Estricta y Arranque en Frío (*Cold-Start*)

1. **Exclusión Estricta:** Cualquier libro que el usuario ya tenga registrado en su biblioteca (`UserBook`) o listas de lectura personales es estrictamente descartado antes de entrar al proceso de scoring.
2. **Cold-Start Fallback:** Para lectores noveles sin historial suficiente, el motor complementa automáticamente la lista con obras aclamadas de la comunidad (`num_readers` y `average_rating` elevados), manteniendo el formato y versionado `algorithm_version = "v1"`.

---

## 5. Telemetría y Feedback Loop

Los eventos de interacción sobre recomendaciones se registran en el modelo `RecommendationFeedback`:
- Acciones: `recommendation_shown`, `recommendation_clicked`, `book_opened`, `wishlist_added`, `reading_started`, `reading_finished`, `rated`.
- Versión auditada: `algorithm_version = "v1"`.
- Permite calcular métricas de conversión y CTR por estrategia y versión de algoritmo a través de `GET /api/v1/books/recommendations/metrics/`.
