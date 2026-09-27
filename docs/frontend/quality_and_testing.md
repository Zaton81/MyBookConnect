# Calidad y Estrategia de Pruebas de Frontend (Fase 10)

Este documento detalla las herramientas, estándares de calidad, configuración de linting, formateo de código, pruebas unitarias y pruebas de extremo a extremo (E2E) implementadas para el frontend de BookSocial / MyBookConnect.

---

## 1. Scripts Estandarizados (`package.json`)

El frontend cuenta con un ciclo de desarrollo y control de calidad estándar e interoperable con CI/CD:

```bash
# Desarrollo local
pnpm dev              # Inicia servidor Vite en modo desarrollo
pnpm build            # Compila la aplicación para producción (Vite build)
pnpm preview          # Previsualiza la build de producción

# Verificación de tipos y linting
pnpm typecheck        # Ejecuta tsc --noEmit para validar TypeScript
pnpm lint             # Analiza el código con ESLint
pnpm lint:fix         # Corrige automáticamente problemas detectados por ESLint

# Formateo de código
pnpm format           # Aplica formato con Prettier a src/**/*.{ts,tsx,css,json}
pnpm format:check     # Verifica que el código cumpla con el estilo Prettier

# Pruebas automatizadas
pnpm test             # Ejecuta la suite de pruebas unitarias/componentes con Vitest
pnpm test:watch       # Modo interactivo watch de Vitest
pnpm test:ui          # Interfaz visual de Vitest
pnpm test:coverage    # Cobertura de código con c8/v8
pnpm test:e2e         # Ejecuta pruebas End-to-End con Playwright
```

---

## 2. Linters y Formateadores

### ESLint (`.eslintrc.cjs`)
Se ha configurado ESLint con los siguientes plugins clave:
- `@typescript-eslint/eslint-plugin` y `@typescript-eslint/parser`: Para análisis estático robusto de TypeScript.
- `eslint-plugin-react` y `eslint-plugin-react-hooks`: Para garantizar cumplimiento de las reglas fundamentales de React y hooks (`exhaustive-deps`).
- `eslint-plugin-react-refresh`: Para soporte óptimo de HMR en Vite.
- `eslint-plugin-jsx-a11y`: Para garantizar accesibilidad web (roles ARIA, eventos de teclado en elementos interactivos).

### Prettier (`.prettierrc` y `.prettierignore`)
Estilo consistente en todo el equipo de desarrollo:
- `semi`: `true`
- `singleQuote`: `true`
- `tabWidth`: `2`
- `trailingComma`: `'es5'`
- `printWidth`: `100`

---

## 3. Pruebas Unitarias y de Componentes (Vitest + React Testing Library)

Las pruebas unitarias y de componentes se ejecutan bajo `vitest` con entorno `jsdom` y mocks controlados para stores (`zustand`) y peticiones HTTP (`fetch`).

### Cobertura de Suites:
1. **Autenticación:**
   - [Login.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/auth/__tests__/Login.test.tsx): Formulario de login, credenciales y errores.
   - [Register.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/auth/__tests__/Register.test.tsx): Registro de usuario y validaciones.
2. **Navegación y UX:**
   - [ScrollToTop.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/components/layout/__tests__/ScrollToTop.test.tsx): Validación del restablecimiento instantáneo del scroll a `(0, 0)` en cada cambio de ruta.
3. **Catálogo y Libros:**
   - [BookDetail.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/books/__tests__/BookDetail.test.tsx): Carga de detalles, metadatos y estados de error.
   - [ReadingLists.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/books/__tests__/ReadingLists.test.tsx): Pestañas, creación y renderizado de colecciones.
4. **Biblioteca y Reseñas:**
   - [Library.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/library/__tests__/Library.test.tsx): Carga y visualización de libros personales.
   - [ReviewForm.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/reviews/__tests__/ReviewForm.test.tsx): Render y envío de valoraciones.
5. **Comunidad y Perfiles:**
   - [Profile.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/profile/__tests__/Profile.test.tsx): Perfil propio, estadísticas, privacidad y acceso restringido (403).
   - [SocialInteractions.test.tsx](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/features/social/__tests__/SocialInteractions.test.tsx): Seguidores, seguidos y relaciones de amistad.

---

## 4. Pruebas End-to-End (Playwright)

### Configuración (`playwright.config.ts`):
- Directorio de pruebas: `./e2e`
- URL base: `http://localhost:5173`
- Configuración para modo headless en CI con reintentos y capturas de pantalla en fallos.

### Flujos Críticos Cubiertos (`e2e/critical-flows.spec.ts`):
- **Flujo 1:** Carga de página principal y navegación hacia catálogo.
- **Flujo 2:** Formulario de inicio de sesión y validaciones de campo.
- **Flujo 3:** Formulario de registro y validación de campos.
- **Flujo 4:** Navegación entre páginas y verificación de `ScrollToTop` (scroll vuelve a 0 tras desplazamiento).

---

## 5. Experiencia de Usuario: Scroll-to-Top Automático

Para resolver el problema de persistencia indeseada de la posición del scroll al navegar entre páginas (por ejemplo, desde el final de la página de estadísticas hacia la lista de amigos), se incorporó el componente [ScrollToTop](file:///C:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/frontend/src/components/layout/ScrollToTop.tsx):

```tsx
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'instant',
    });
  }, [pathname]);

  return null;
}
```

Este componente se encuentra integrado en la raíz del enrutador de React (`router.tsx`), garantizando que cualquier transición de ruta restablezca el scroll al inicio de forma inmediata.
