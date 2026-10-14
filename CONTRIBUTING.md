# Guía de Contribución y Gobernanza — My Book Social

¡Bienvenido al proyecto **My Book Social**! Este documento establece los estándares de calidad, flujo de trabajo con ramas Git, directrices para pruebas y directivas de interacción tanto para desarrolladores humanos como para agentes autónomos de IA.

---

## 1. Principios Fundamentales y Filosofía
1. **Calidad y Cero Atajos:** Ningún cambio se fusiona sin suites de pruebas automatizadas verdes, linters limpios y revisión de impacto en producción.
2. **Seguridad por Diseño (P0):** Credenciales en variables de entorno o gestores de secretos; cookies `HttpOnly` para JWT; cero exposición de puertos internos.
3. **Optimización Invariante $O(1)$:** Cero tolerancia a consultas N+1 en endpoints de listado o feeds.
4. **Unificación de Marca:** La identidad oficial del proyecto es **My Book Social** (`mybooksocial.com`). Queda prohibido reintroducir referencias a dominios antiguos.

---

## 2. Flujo de Ramas (Branching Strategy)

Seguimos una metodología rigurosa basada en `develop` y `main`:

```
main (Producción estable, solo tags anotados)
  ▲
  │ (Release PR / Hotfix)
develop (Entorno de integración y desarrollo activo)
  ▲
  ├── feat/nombre-funcionalidad
  ├── fix/correccion-bug
  └── chore/mantenimiento
```

- **Rama Base de Trabajo:** Todo nuevo desarrollo o refactorización DEBE ramificarse y fusionarse contra **`develop`**.
- **Rama Protegida `main`:** Queda **terminantemente prohibido hacer commits directos a `main`**. Los cambios solo llegan a `main` a través de Pull Requests de release o hotfixes críticos aprobados.

---

## 3. Convenciones de Commits Semánticos

Todos los mensajes de confirmación deben seguir la especificación [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<ámbito opcional>): <descripción concisa en imperativo y minúsculas>

[cuerpo explicativo opcional]
```

### Tipos Permitidos:
- `feat`: Nueva funcionalidad o capacidad para el usuario.
- `fix`: Corrección de un fallo o error en el sistema.
- `docs`: Modificación o añadido exclusivo de documentación.
- `style`: Formateo de código sin alteración de lógica.
- `refactor`: Cambio de código que no añade funcionalidades ni corrige errores.
- `perf`: Optimización demostrada de rendimiento o reducción de consultas SQL.
- `test`: Añadido o refactorización de suites de pruebas.
- `chore`: Tareas de mantenimiento de dependencias, scripts de build o configuración.

---

## 4. Estándares de Código y Linters

### Backend (Python / Django)
- **Formateador y Linter:** `ruff`
- **Comprobación:**
  ```bash
  docker compose exec backend ruff check .
  ```
- **Reglas:** Importaciones ordenadas según PEP8, tipado explícito, sin imports no utilizados y sin comprensiones innecesarias.

### Frontend (React / TypeScript)
- **Linter:** `eslint`
- **Comprobación:**
  ```bash
  cd frontend && npm run lint
  ```
- **Reglas:** TypeScript estricto, accesibilidad JSX (`jsx-a11y`), sin variables no utilizadas (`@typescript-eslint/no-unused-vars`).

---

## 5. Checklist de Definition of Done (DoD)

Antes de abrir una Pull Request o marcar una tarea como completada, debe cumplirse la siguiente lista de verificación:

- [ ] **Código y Arquitectura:**
  - [ ] Respeta los Architecture Decision Records ([docs/decisions/](file:///c:/Users/zaton/Desktop/Escritorio/proyectos/MyBookConnect/docs/decisions/README.md)).
  - [ ] No introduce consultas N+1 en DRF (demostrado con tests si afecta a serializers).
- [ ] **Pruebas Automatizadas:**
  - [ ] Backend: Pruebas unitarias e integración en `pytest` pasando al 100%.
  - [ ] Frontend: Pruebas unitarias en `vitest` (`npm run test:run`) pasando al 100%.
- [ ] **Linters y Formato:**
  - [ ] `ruff check .` con 0 errores.
  - [ ] `npm run lint` con 0 errores.
- [ ] **Trazabilidad y Documentación:**
  - [ ] Registro en `CHANGELOG.md` bajo la sección `## [Unreleased]`.
  - [ ] Estado actualizado en `Roadmap.md` y `memory.md`.

---

## 6. Protocolo Obligatorio para Agentes de IA

Si interactúas como un asistente de codificación con IA (Antigravity, Cursor, Claude, Copilot):

1. **Lectura Previa de Contexto:** Revisa obligatoriamente `instruccionesAgente.md`, `memory.md` y los ADRs antes de proponer cambios estructurales.
2. **Prohibición de Modificaciones a Ciegas:** No ejecutes cambios en código sin presentar primero un plan de implementación formal en un artefacto estructurado.
3. **No Suprimir Tests Existentes:** Si un test falla tras una modificación, adapta el código para satisfacer la invariante del test o justifica y acuerda la actualización del contrato con el usuario.
4. **Verificación Sistemática de Nombres y Marcas:** Toda URL, remitente de correo o referencia de marca debe apuntar a **My Book Social** (`mybooksocial.com`).
