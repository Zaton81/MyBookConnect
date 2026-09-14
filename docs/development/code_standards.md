# Estándares de Código y Directrices de Calidad

## 1. Backend (Python / Django)
- **Formateo y Linter:** Uso de `ruff` configurado en `backend/pyproject.toml`.
  - Longitud máxima de línea: 120 caracteres.
  - Ordenación automática de imports (`isort`).
- **Comprobación de Tipos:** Anotaciones de tipos de Python 3.12 (`typing`, `Union` con `|`).
- **Convenciones:**
  - Nombres de clases: `PascalCase`.
  - Nombres de funciones y variables: `snake_case`.
  - Constantes: `UPPER_SNAKE_CASE`.
- **Lógica de Negocio:** Mantener las vistas delgadas (*thin views*) delegando la lógica pesada en `books.services`.
- **Preservación de Comentarios:** Mantener la integridad de los docstrings y comentarios existentes.

---

## 2. Frontend (React / TypeScript)
- **TypeScript Estricto:** `strict: true` en `tsconfig.json`. Prohibido el uso de `any` salvo excepciones estrictamente tipadas en mocks de test.
- **Componentes:** Componentes funcionales con Hooks reutilizables.
- **Formularios:** Validación desacoplada con `react-hook-form` y esquemas de `zod`.
- **CSS:** Clases utilitarias de TailwindCSS con diseño adaptativo (*mobile-first*). Evitar estilos inline.
- **Nombres de Archivos:**
  - Componentes y Páginas: `PascalCase.tsx` (p. ej. `BookDetail.tsx`, `Navbar.tsx`).
  - Hooks y utilidades: `camelCase.ts` (p. ej. `useAuth.ts`, `media.ts`).
