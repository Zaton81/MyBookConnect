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
- Versiones auditadas: `algorithm_version = "v1"` y `algorithm_version = "v2"`.
- Permite calcular métricas de conversión y CTR por estrategia y versión de algoritmo a través de `GET /api/v1/books/recommendations/metrics/`.

---

## 6. Motor de Recomendaciones v2 (`RecommendationEngineV2` — User-User Similarity)

Implementado en `backend/books/services/recommendation_v2_service.py` para la **Fase 50**:
$$\text{Usuario Objetivo} \longrightarrow \text{Lectores Afines (K-NN)} \longrightarrow \text{Libros no leídos por el objetivo} \longrightarrow \text{Ranking Colaborativo v2}$$

### Modelado de Afinidad Usuario-Usuario
La similitud entre el usuario objetivo $U$ y un lector candidato $V$ combina la intersección de biblioteca con la coherencia en valoraciones numéricas:
1. **Coeficiente de Jaccard:**
   $$J(U, V) = \frac{|Books(U) \cap Books(V)|}{|Books(U) \cup Books(V)|}$$
2. **Consistencia de Calificaciones:**
   Para cada libro común $b$, se evalúa la desviación absoluta $|r_{u,b} - r_{v,b}|$, normalizada a escala $[0, 1]$.
3. **Similitud Combinada:**
   $$\text{sim}(U, V) = 0.55 \cdot J(U, V) + 0.45 \cdot \text{RatingSim}(U, V)$$
   (con boost estadístico cuando comparten 3 o más libros).

### Extracción de Candidatos y Puntuación Colaborativa
Para cada libro $B$ leído o calificado por los vecinos similares que $U$ no tiene en su biblioteca:
$$S_{\text{collab}}(B) = \frac{\sum_{V \in \text{Peers}(B)} \text{sim}(U, V) \cdot \text{weight}(V, B)}{\sum_{V \in \text{Peers}(B)} \text{sim}(U, V)}$$

### Fusión Híbrida v2
$$S_{\text{v2}} = \beta \cdot S_{\text{collab}} + (1 - \beta) \cdot S_{\text{v1}}$$
- $\beta = 0.50$ cuando existen lectores afines con lecturas candidatas.
- Si el usuario es nuevo o no tiene vecinos con lecturas no exploradas, el motor recurre transparentemente al motor canónico de contenido v1 ($\beta = 0$).

### Endpoints Disponibles
- `GET /api/v1/books/recommendations/?strategy=v2`: Recomendaciones v2 con desglose colaborativo (`breakdown.collaborative`, `breakdown.shared_peers`, `breakdown.top_peer`).
- `GET /api/v1/books/recommendations/similar-readers/`: Consulta de lectores más afines (*lectores gemelos*) con score de similitud y conteo de obras comunes.

---

## 7. Motor de Recomendaciones v3 (`RecommendationEngineV3` — Embeddings Semánticos y Vector de Preferencias)

Implementado en `backend/books/services/recommendation_v3_service.py` para la **Fase 51**:
$$\text{Libros Consumidos} \longrightarrow \text{Promedio Ponderado} \longrightarrow \vec{U} \text{ (User Preference Embedding)} \longrightarrow \text{Similitud Coseno} \longrightarrow \text{Fusión Tri-Híbrida v3}$$

### Vector de Preferencias Sintético de Usuario ($\vec{U}$)
Condensa la orientación temática y de estilo de un usuario sin necesidad de entrenamiento periódico, derivándolo de las obras con las que ha interactuado:
$$\vec{U}_{\text{raw}} = \frac{\sum_{i} w_i \cdot \vec{E}(B_i)}{\sum_{i} w_i}$$
Donde los factores de ponderación $w_i$ priorizan:
- **Libros con calificación de 5 estrellas:** $w_i = 1.50$
- **Libros con calificación de 4 estrellas:** $w_i = 1.20$
- **Libros terminados (`READ`):** $w_i = 1.00$
- **Libros en curso (`READING`):** $w_i = 0.70$
- **Libros en lista de deseos (`WANT_TO_READ`):** $w_i = 0.50$

El vector final es normalizado en la esfera euclídea unitaria:
$$\hat{U} = \frac{\vec{U}_{\text{raw}}}{\|\vec{U}_{\text{raw}}\|_2}$$

### Afinidad Semántica con Candidatos ($S_{\text{semantic}}$)
Para cualquier libro candidato $B$ no consumido con embedding $\vec{E}(B)$:
$$S_{\text{semantic}}(B) = \max\left(0.0, \cos(\hat{U}, \vec{E}(B))\right) = \max\left(0.0, \frac{\hat{U} \cdot \vec{E}(B)}{\|\hat{U}\| \|\vec{E}(B)\|}\right)$$

### Fusión Tri-Híbrida v3
Combina semántica profunda, señal comunitaria colaborativa (v2) y canónicas de contenido (v1):
$$S_{\text{v3}} = 0.45 \cdot S_{\text{semantic}} + 0.30 \cdot S_{\text{collab}} + 0.25 \cdot S_{\text{content\_v1}}$$
- Si el usuario aún no posee vector de preferencias (arranque en frío o libros sin embeddings), el motor recurre a la ponderación colaborativa/canónica v2/v1 asegurando recomendaciones de alta calidad y versionadas como `algorithm_version = "v3"`.

### Explicabilidad v3
- `algorithm_version`: `"v3"`.
- `breakdown`: Contiene `semantic`, `collaborative`, `content_v1`, `has_user_embedding`, además del desglose detallado de variables canónicas.
- `reason`: Motivo contextualizado cuando predomina la similitud semántica (*"Afinidad semántica profunda con los temas y estilo de tus libros favoritos"*).

### Endpoints Disponibles
- `GET /api/v1/books/recommendations/?strategy=v3`: Recomendaciones tri-híbridas v3 con desglose semántico.
- `GET /api/v1/books/recommendations/user-embedding/`: Consulta del vector sintético de preferencias del lector, dimensionalidad, cantidad de obras analizadas y componentes vectoriales para inspección y visualización.

---

## 8. Recomendaciones Explicables (Fase 52)

### Objetivos y Enfoque Multi-Señal
El módulo de recomendaciones explicables (`RecommendationExplanationEngine` en `backend/books/services/recommendation_explanation_service.py`) transforma las puntuaciones matemáticas de los algoritmos en explicaciones transparentes, persuasivas y comprensibles para el lector, respondiendo a la pregunta fundamental: **¿Por qué te recomendamos este libro?**

### Tipos de Evidencia Extraída
1. **Temático-Literaria (`genre`)**:
   - Analiza el historial lector del usuario en los géneros del libro recomendado.
   - Ejemplo: *"Te han gustado 5 libros de Ciencia Ficción"*.
2. **Autor y Obras Ancla (`author`)**:
   - Detecta si el lector ha leído o calificado con alta puntuación obras previas del mismo autor.
   - Ejemplo: *"Has valorado 1984 con 5 estrellas"*.
3. **Semántico-Conceptual (`semantic`)**:
   - Compara el vector de embedding del candidato contra las obras leídas o favoritas usando similitud coseno.
   - Ejemplo: *"Tiene similitud semántica alta con Fundación (88%)"*.
4. **Red Social (`social`)**:
   - Consulta el grafo social del usuario (amigos o autores seguidos) que hayan leído la obra.
   - Ejemplo: *"3 usuarios que sigues lo han leído (@amigo1, @amigo2)"*.
5. **Colaborativa Comunitaria (`collaborative`)**:
   - Respaldo de lectores con gustos afines (vecinos k-NN o gemelos de lectura).
   - Ejemplo: *"Lectores con gustos afines (@lector1) han disfrutado de este libro"*.
6. **Comunidad y Deseos (`community` / `wishlist`)**:
   - Calificación promedio destacada en la comunidad o inclusión en la lista de deseos del usuario.

### Estructura de la Explicación
Cada recomendación en las APIs (`v1`, `v2`, `v3`) incluye ahora un objeto estructurado `explanation`:
```json
{
  "headline": "Te recomendamos Dune porque:",
  "primary_reason": "Has valorado 1984 con 5 estrellas",
  "total_signals": 4,
  "algorithm_version": "v3",
  "reasons": [
    {
      "type": "genre",
      "text": "Te han gustado 5 libros de Ciencia Ficción",
      "confidence": 0.95,
      "icon": "book-open",
      "metadata": {"liked_count": 5, "category_name": "Ciencia Ficción"}
    },
    {
      "type": "author",
      "text": "Has valorado 1984 con 5 estrellas",
      "confidence": 0.95,
      "icon": "pen-tool",
      "metadata": {"author": "Frank Herbert", "anchor_book": "1984"}
    },
    {
      "type": "semantic",
      "text": "Tiene similitud semántica alta con Fundación (88%)",
      "confidence": 0.88,
      "icon": "sparkles",
      "metadata": {"anchor_book_title": "Fundación", "similarity": 0.88, "percentage": 88}
    },
    {
      "type": "social",
      "text": "3 usuarios que sigues lo han leído (@amigo1, @amigo2 y 1 más)",
      "confidence": 0.92,
      "icon": "users",
      "metadata": {"count": 3, "followed_readers": ["amigo1", "amigo2"]}
    }
  ]
}
```

### Endpoints
- `GET /api/v1/books/recommendations/<book_id>/explain/`: Endpoint público/autenticado para consultar bajo demanda la justificación multi-señal de un libro específico para el usuario actual.



