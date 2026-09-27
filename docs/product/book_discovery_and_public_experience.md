# Experiencia de Descubrimiento Literario y Home Pública (Fase 20)

## 1. Visión General

La **Fase 20 — Descubrimiento de Libros** aborda la exploración no asistida exclusivamente por Inteligencia Artificial, proporcionando a visitantes y lectores registrados múltiples dimensiones para encontrar lecturas relevantes:
- **Tendencias temporales** (`TrendingBooksView` con `AllowAny`).
- **Libros más populares** según agregaciones de bibliotecas activas (`user_entries`) y valoraciones.
- **Novedades** añadidas al catálogo.
- **Exploración facetada por categorías y géneros** literarios.
- **Home pública visual y moderna** con escaparate dinámico y formularios emergentes (`AuthModal`) para login y registro sin recargas forzadas.

---

## 2. Arquitectura Backend

### 2.1 Endpoint `GET /api/v1/books/discover/`
- Implementado en `backend/books/discovery_views.py`.
- Permiso: `AllowAny`.
- Agregaciones optimizadas con `select_related('author')` y `prefetch_related('categories')`.
- Caché en Redis bajo la clave `books:discovery:v1:{genre}:{limit}` con un TTL de 10 minutos (600 s) mediante `safe_cache_get/set`.

### 2.2 Apertura de Tendencias Públicas
- `TrendingBooksView` en `backend/books/views.py` actualizado a `permission_classes = (permissions.AllowAny,)`.
- Permite renderizar carruseles de tendencias en la Landing sin exigir tokens JWT.

---

## 3. Arquitectura Frontend

### 3.1 Modal de Autenticación Emergente (`AuthModal.tsx`)
- Ubicado en `frontend/src/features/auth/components/AuthModal.tsx`.
- Modal centrado con fondo desenfocado (`backdrop-blur-md bg-slate-950/75`).
- Conmutador con pestañas entre *"Iniciar Sesión"* y *"Crear Cuenta"*.
- Validación instantánea con feedback visual, indicador de fortaleza de contraseña, Google OAuth y atajo de cierre con tecla `Escape`.

### 3.2 Barra de Navegación Pública (`PublicHeader.tsx`)
- Ubicada en `frontend/src/components/layout/PublicHeader.tsx`.
- Integrada en `PublicLayout` cuando el visitante no tiene sesión activa.
- Proporciona botones destacados *"Iniciar sesión"* y *"Crear cuenta gratis"* que abren el modal emergente al instante.

### 3.3 Landing Page Pública (`PublicLandingPage.tsx`)
- Ubicada en `frontend/src/features/discovery/pages/PublicLandingPage.tsx`.
- **Hero Section:** Titular llamativo, badge de comunidad activa, subtítulo inspirador y llamadas a la acción directas.
- **Escaparate en Vivo:** Pestañas para *Tendencias*, *Populares* y *Novedades*, chips de géneros dinámicos y tarjetas de libros con puntuación y autor.
- **Pilares de Confianza:** Estanterías inteligentes, privacidad incondicional (RGPD), comunidad auténtica y BookAI respetuoso.
- **Banner Final:** Llamada a la acción para registrarse en 1 minuto.
