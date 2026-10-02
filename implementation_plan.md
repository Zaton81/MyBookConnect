# Plan de Implementación — RoadmapV3: Sprint 3 (Autores y FAQs)

**Fecha:** 2 de octubre de 2026  
**Rama:** `develop`  
**Estado:** En progreso  
**Objetivo:** Implementar el subsistema integral de autores prioritario de RoadmapV3 (Sección 4: modelo ampliado, verificación, flujo de reclamación `AuthorClaim`, página pública enriquecida y moderación administrativa) e incorporar el nuevo subsistema de FAQs con visualización pública en acordeón y administración en el panel de control.

---

## 1. Alcance y Requisitos del Sprint 3 + FAQs

### 1.1. Subsistema de Autores (Sección 4 RoadmapV3)
- **Modelo de Autor Ampliado (`Author`):**
  - Campos biográficos y de identidad: `nationality`, `birth_date`, `death_date`, `website`, `twitter`, `instagram`, `wikipedia_url`, `canonical_name`, `aliases`, `external_ids`.
  - Estado de verificación: `is_verified` (booleano), `claimed_by` (clave foránea a `User`).
- **Sistema de Reclamación de Autor (`AuthorClaim`):**
  - Modelo `AuthorClaim` con estados `pending`, `approved`, `rejected`, `cancelled`.
  - Solicitud desde la interfaz pública del autor por lectores registrados (`POST /api/v1/books/authors/<id>/claim/`).
  - Consulta de estado del reclamo (`GET /api/v1/books/authors/<id>/claim-status/`).
  - Restricciones: una sola solicitud pendiente por autor/usuario; autores ya verificados no pueden ser reclamados arbitrariamente.
- **Moderación Administrativa de Reclamaciones:**
  - Endpoint administrativo para listar y filtrar reclamos (`GET /api/v1/admin/author-claims/`).
  - Resolución de reclamos (`POST /api/v1/admin/author-claims/<id>/resolve/`): aprobación (marca autor verificado, asigna a usuario, sincroniza `AuthorProfile`, emite notificación) o rechazo (guarda notas y notifica).
- **Página Pública de Autor Mejorada en Frontend:**
  - Insignia visual de verificación ("Autor Verificado").
  - Metadatos biográficos, enlaces sociales y enlaces externos.
  - Estadísticas públicas agregadas: valoración promedio, libros en catálogo, volumen de reseñas y total de lectores.
  - Botón y modal accesible para reclamar la página.

### 1.2. Subsistema de FAQs (Preguntas Frecuentes)
- **Modelo Backend (`FAQ`):**
  - Campos: `question`, `answer`, `category` (`general`, `authors`, `books`, `account`, `community`), `order`, `is_published`, `created_at`, `updated_at`.
- **Endpoints de la API:**
  - Público: `GET /api/v1/faqs/` (devuelve FAQs publicadas ordenadas por categoría y orden numérico).
  - Admin: CRUD completo (`GET`, `POST`, `PATCH`, `DELETE` en `/api/v1/admin/faqs/`).
  - Fixtures o sembrado inicial con preguntas frecuentes de utilidad.
- **Frontend:**
  - Vista pública `/faqs` con componente **Acordeón interactivo** (animación de despliegue al hacer clic, soporte de teclado, buscador por texto y filtros por categoría).
  - Enlaces a FAQs en cabecera (`Header`) y pie de página (`Footer`).
  - Pestaña de administración de FAQs en `AdminDashboard` (`AdminFaqsTab.tsx`): creación rápida, edición, cambio de estado publicado/borrador y eliminación.

---

## 2. Plan de Pruebas

- **Backend (`tests/test_sprint3_authors_and_faqs.py`):**
  - Creación de solicitud `AuthorClaim` por usuario autenticado.
  - Rechazo de reclamaciones duplicadas pendientes para el mismo autor.
  - Aprobación administrativa de reclamo: autor pasa a `is_verified=True`, vinculación con `User` y `AuthorProfile`.
  - Rechazo administrativo de reclamo con registro de notas de moderación.
  - Serialización enriquecida de autor con estadísticas de lectores y reseñas.
  - Endpoint público de FAQs: solo devuelve ítems con `is_published=True`.
  - Endpoint administrativo de FAQs: solo accesible a staff, soporte de CRUD completo.
- **Frontend:**
  - Typecheck y comprobación de build con Vite (`npm run build`).

---

## 3. Criterios de Aceptación (Definition of Done)

- [ ] Modelo `Author` ampliado con metadatos de identidad y verificación.
- [ ] Modelo `AuthorClaim` y flujo de reclamación implementado y protegido.
- [ ] Panel de administración con pestaña de gestión de reclamaciones de autor y pestaña de FAQs.
- [ ] Página de autor en frontend con insignia de verificación, estadísticas y modal de reclamo.
- [ ] Página pública `/faqs` en formato acordeón responsivo y accesible.
- [ ] 100% de tests pasando en backend y build frontend limpio.
- [ ] Commit semántico y push a `develop`.
