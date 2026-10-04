# Plan de Implementación — RoadmapV3: Sprint 5 (Calidad, Rendimiento, Accesibilidad WCAG y CI/CD — P2)

**Fecha:** 4 de octubre de 2026  
**Rama de trabajo:** `develop`  
**Estado:** Propuesto para revisión y aprobación  
**Prioridad:** P2 (Calidad de Software, Rendimiento y Preparación para el Lanzamiento)

---

## 1. Contexto y Objetivos

El **Sprint 5 de RoadmapV3** consolida la calidad global del sistema, cubriendo las Secciones **13 (Frontend y Accesibilidad)**, **14 (Seguridad y Sanitización)**, **18 (Idempotencia y Resiliencia)**, **19 (Testing)**, **20 (CI/CD y Deploy Checks)** y **23 (Performance Backend y Erradicación de N+1)**.

### Objetivos Principales:
1. **TypeScript Strict y Typecheck Limpio (Frontend):**
   - Subsanar todas las advertencias y errores de `tsc --noEmit` (`noUnusedLocals`) en componentes administrativos, de catálogo, FAQs y búsqueda global.
   - Garantizar que `npm run typecheck` concluya con **cero errores (código 0)**.
2. **Accesibilidad WCAG 2.1 AA y Usabilidad (UX):**
   - Asegurar roles y atributos semánticos accesibles en componentes interactivos:
     - Acordeón de FAQs (`aria-expanded`, `aria-controls`, `role="region"`).
     - Buscador global y filtros (`aria-label`, estados de foco con `focus-visible`).
     - Imágenes con texto alternativo (`alt`) coherente para lectores de pantalla.
3. **Rendimiento Backend y Erradicación de Consultas N+1:**
   - Auditar y optimizar consultas en `GlobalSearchView` y `UnifiedBookSearchView` garantizando complejidad $O(1)$ en consultas SQL (`select_related`, `prefetch_related`).
   - Verificar tiempos de respuesta bajo presupuesto estricto (< 100ms en búsqueda y catálogo).
4. **Seguridad y Sanitización HTML (XSS):**
   - Validar que las entradas enriquecidas y de usuario se procesen mediante `sanitize_plain_text` y `DOMPurify`, impidiendo inyecciones de scripts maliciosos.
5. **Testing Automatizado Exhaustivo:**
   - Nuevos tests de frontend en Vitest para `SearchPage` y `FaqsPage`.
   - Nueva suite de backend `test_sprint5_quality_and_performance.py` verificando ausencia de N+1, rendimiento de consultas, integridad transaccional y robustez de contratos de API.

---

## 2. Modificaciones Técnicas Propuestas

### 2.1. Limpieza de TypeScript (`frontend/src/`)
- Corregir imports no utilizados en:
  - `src/features/admin/components/AdminAuthorClaimsTab.tsx`
  - `src/features/books/pages/Author.tsx`
  - `src/features/discovery/pages/SearchPage.tsx`
  - `src/features/faqs/pages/FaqsPage.tsx`
- Ejecutar y validar `npm run typecheck` (`tsc --noEmit`).

### 2.2. Accesibilidad WCAG y UX
- En `src/features/faqs/pages/FaqsPage.tsx`:
  - Añadir `id`, `aria-expanded={isOpen}`, `aria-controls={`faq-answer-${faq.id}`}` al botón del acordeón.
  - Añadir `id={`faq-answer-${faq.id}`}`, `role="region"`, `aria-labelledby={`faq-question-${faq.id}`}` al contenedor colapsable.
- En `src/features/discovery/pages/SearchPage.tsx`:
  - Añadir `aria-label="Término de búsqueda"` al input y `role="tablist"` / `role="tab"` a los botones de categorías ("Todo", "Libros", "Autores", "Lectores").
  - Asegurar contraste y anillos de foco visibles (`focus-visible:ring-2 focus-visible:ring-teal-500`).

### 2.3. Optimización de Rendimiento Backend (`backend/books/search_views.py`)
- Optimizar `GlobalSearchView`:
  - Para libros: `select_related('author').prefetch_related('categories', 'authors')`.
  - Para autores: `prefetch_related('books')`.
  - Limitar campos diferidos innecesarios si aplica (`defer('embedding')`).

### 2.4. Pruebas Automatizadas
1. **Frontend (Vitest):**
   - `src/features/discovery/__tests__/SearchPage.test.tsx`: renderizado, búsqueda reactiva, cambio de pestañas y visualización de resultados.
   - `src/features/faqs/__tests__/FaqsPage.test.tsx`: despliegue del acordeón interactivo al hacer click y filtros por categoría.
2. **Backend (pytest):**
   - `backend/tests/test_sprint5_quality_and_performance.py`:
     - Test de conteo de queries SQL en `/api/v1/search/` (con Django `assertNumQueries`).
     - Test de resiliencia y sanitización ante payloads con inyección HTML/scripts.
     - Test de verificación de contratos y accesibilidad de endpoints clave.

---

## 3. Plan de Pruebas y Validación

1. **Typecheck y Linters de Frontend:**
   - `npm run typecheck` en `frontend/` (0 errores).
   - `npm run test` en `frontend/` (31 tests previos + nuevos tests pasando al 100%).
   - `npm run build` en `frontend/` (código 0).
2. **Regresión Backend Completa Secuencial:**
   - Ejecutar Sprints 1 a 5:
     `pytest tests/test_sprint1_security.py tests/test_sprint2_infrastructure.py tests/test_sprint3_authors_and_faqs.py tests/test_sprint4_catalog_deduplication.py tests/test_sprint5_quality_and_performance.py`
3. **Verificación de Sistema Django:**
   - `python manage.py check` limpio en el contenedor backend.

---

## 4. Criterios de Aceptación (Definition of Done)

- [ ] `npm run typecheck` pasa con 0 errores TypeScript.
- [ ] Atributos ARIA y mejoras WCAG implementadas y operativas en FAQs y Búsqueda.
- [ ] Cero consultas N+1 en las vistas optimizadas de búsqueda y catálogo.
- [ ] 100% de tests pasando en backend y frontend sin regresiones.
- [ ] Documentación actualizada (`RoadmapV3.md`, `memory.md`, `CHANGELOG.md`).
- [ ] Commit semántico y push a `develop`.
