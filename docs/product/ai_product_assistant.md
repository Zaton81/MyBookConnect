# Fase 24 — IA de Producto y Asistente Literario BookAI

## 1. Visión y Objetivos

La **Fase 24 — IA de Producto** eleva la experiencia del lector integrando inteligencia artificial generativa contextualmente conectada con el catálogo y la biblioteca personal. Proporciona herramientas avanzadas de exploración literaria, explicación analítica en profundidad y comparativas entre obras, respetando siempre principios éticos de transparencia mediante etiquetado explícito y disclaimers.

Adicionalmente, se consolida la **unificación total del sistema de calificaciones a escala de 1 a 5 estrellas** en toda la plataforma, resolviendo inconsistencias históricas donde notas privadas sobre 10 distorsionaban el desglose y las métricas de lectura.

---

## 2. Capacidades de la IA de Producto

### A. Explicación Literaria en Profundidad (`AIExplainBookView`)
- **Endpoint:** `POST /api/v1/books/<pk>/ai/explain/`
- **Propósito:** Generar una guía de lectura integral para una obra específica con estructura enriquecida:
  1. **🏛️ Contexto Histórico y de Creación:** Época, circunstancias del autor y contexto sociocultural.
  2. **🔑 Claves Temáticas Fundamentales:** Ejes conceptuales, dilemas éticos y temas centrales.
  3. **🖋️ Estilo Narrativo y Voz del Autor:** Ritmo, técnicas narrativas y atmósfera.
  4. **💡 Guía de Lectura y Perfil de Lector:** Recomendación personalizada de disfrute.
- **Transparencia obligatoria:** Retorna siempre `is_ai_generated: true`, `badge: "✨ Generado por IA"` y un disclaimer legal y divulgativo.
- **Fallback Determinista:** Si el proveedor neuronal no se encuentra disponible, genera un análisis estructural basado en la catalogación existente sin romper el flujo de usuario.

### B. Comparativas Temáticas entre Obras (`AICompareBooksView`)
- **Endpoint:** `POST /api/v1/books/ai/compare/`
- **Payload:** `{"book_a_id": <int>, "book_b_id": <int>}`
- **Propósito:** Contrastar dos títulos distintos del catálogo para orientar al lector en elecciones literarias:
  1. **🔗 Puntos de Convergencia:** Afinidades temáticas y paralelismos estilísticos.
  2. **⚡ Contrastes y Enfoques Distintivos:** Diferencias de ritmo, visión del mundo y profundidad.
  3. **🧭 Recomendación de Orden y Experiencia Lectora:** Criterio sobre cuál abordar primero según el estado anímico o preferencias.
- **Validaciones:** Impide comparar el mismo libro contra sí mismo (`400 Bad Request`) y valida existencia de ambos ejemplares en el catálogo (`404 Not Found`).

### C. Resúmenes Estructurados y Etiquetado de Transparencia
- **Endpoint:** `POST /api/v1/books/<pk>/ai/summary/`
- Se actualizó el contrato para incluir de manera fija:
  - `is_ai_generated: true`
  - `badge: "✨ Generado por IA"`
  - `disclaimer: "✨ Contenido generado por Inteligencia Artificial con fines orientativos y divulgativos."`

### D. Asistente Literario Conversacional (BookAI)
- Contextualización automática con las lecturas recientes del usuario (`UserBook`).
- Sugerencias rápidas orientadas a comparativas temáticas y contexto histórico.
- Badge identificativo `✨ Generado por IA` en cabecera y disclaimer en el pie del diálogo.

---

## 3. Unificación del Sistema de Calificaciones (Escala 1 a 5 Estrellas)

Se identificó y corrigió el fallo estructural donde notas privadas utilizaban rangos de 1 a 10 mientras las reseñas y modelos base operaban sobre 1 a 5:

1. **`StarRating.tsx`:**
   - Estandarizado a `maxRating = 5` por defecto.
   - Eliminada la división `rating / 2` que reducía visualmente calificaciones válidas (un 4.5/5 se mostraba erróneamente como 2.25/5).
2. **`BookDetail.tsx`:**
   - Selector de nota privada actualizado a opciones `[5, 4, 3, 2, 1]` con etiqueta `⭐ N de 5 estrellas`.
   - Visualización de nota privada normalizada a `⭐ N/5`.
3. **`AddBook.tsx` & `Library.tsx`:**
   - Selectores rápidos actualizados a escala `[5, 4, 3, 2, 1]`.
4. **`ReadingStats.tsx`:**
   - Histograma de distribución de notas alineado con el backend (`stats_service.py` genera notas de 1 a 5). Se eliminaron las barras vacías 6-10 y se ajustaron los umbrales de color para destacar lecturas sobresalientes (4-5 estrellas).

---

## 4. Garantías de Calidad y Pruebas

- **Backend:** Suite `backend/tests/test_phase24_product_ai.py` con 9 tests unitarios e integrados pasando al 100%.
- **Frontend:** 27 tests pasando en Vitest (`pnpm test`), 0 errores de tipado TypeScript (`pnpm typecheck`), 0 errores de formateo (`pnpm format:check`) y build de producción verificado (`pnpm build`).
