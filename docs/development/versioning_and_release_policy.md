# Política de Versionado SemVer y Ciclo de Release — My Book Social

Este documento define la gobernanza de versiones, el flujo de publicación de releases y la política de parches de seguridad para **My Book Social**.

---

## 1. Esquema de Versionado: SemVer 2.0.0

My Book Social se adhiere estrictamente a [Semantic Versioning 2.0.0](https://semver.org/lang/es/):

$$\text{Versión} = \mathbf{MAJOR}.\mathbf{MINOR}.\mathbf{PATCH}$$

### 1.1. Incremento de `MAJOR` (Ejemplo: `1.0.0` $\to$ `2.0.0`)
Se incrementa cuando se introducen **cambios incompatibles hacia atrás (Breaking Changes)**:
- Ruptura de contratos públicos de API REST (OpenAPI) o WebSockets que requiera migración por parte de clientes externos.
- Migraciones de base de datos no lineales que exijan tiempos de inactividad o reestructuración destructiva de datos.
- Reemplazo completo de la arquitectura o dependencias de infraestructura base (ej. cambio de motor de base de datos).

### 1.2. Incremento de `MINOR` (Ejemplo: `1.0.0` $\to$ `1.1.0`)
Se incrementa cuando se añade **nueva funcionalidad compatible hacia atrás**:
- Nuevos endpoints en la API que amplían capacidades sin alterar respuestas existentes.
- Nuevas características de producto (ej. clubs de lectura, gamificación, filtros de búsqueda).
- Mejoras sustanciales de rendimiento o adición de índices de base de datos no bloqueantes.

### 1.3. Incremento de `PATCH` (Ejemplo: `1.0.0` $\to$ `1.0.1`)
Se incrementa para **correcciones de errores compatibles hacia atrás**:
- Correcciones de bugs en backend o frontend.
- Parches de seguridad de vulnerabilidades menores sin alteración de contratos.
- Ajustes de estilos, textos o traducciones.

---

## 2. Ciclo de Vida de una Release

```
1. develop ──────────► 2. release/vX.Y.Z ──────────► 3. main (Tag vX.Y.Z)
   (Integración)          (Congelamiento QA)              │ (Despliegue Prod)
                                                          ▼
                                                    4. develop (Back-merge)
```

### Paso 1: Congelamiento de Características (Feature Freeze)
Cuando todas las funcionalidades de una fase o sprint están en `develop` y pasan la suite de pruebas:
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0
```

### Paso 2: Preparación y Auditoría de Release
En la rama `release/vX.Y.Z`:
1. Ejecutar suites completas de pruebas y linters:
   ```bash
   docker compose exec backend pytest
   cd frontend && npm run test:run && npm run lint
   ```
2. Ejecutar pruebas de regresión y preflight:
   ```bash
   bash scripts/production/preflight_prod.sh
   ```
3. Mover entradas de `## [Unreleased]` a `## [X.Y.Z] - YYYY-MM-DD` en `CHANGELOG.md`.

### Paso 3: Fusión a `main` y Etiquetado Git
```bash
git checkout main
git merge --no-ff release/v1.0.0 -m "release: v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0: Producción y Hardening de Seguridad"
git push origin main --tags
```

### Paso 4: Sincronización con `develop`
```bash
git checkout develop
git merge --no-ff main -m "chore: merge release v1.0.0 back to develop"
git push origin develop
git branch -d release/v1.0.0
```

---

## 3. Procedimiento para Hotfixes Críticos (P0)

En caso de detectarse una vulnerabilidad de seguridad crítica o un fallo P0 en producción:

1. **Ramificar desde `main`:**
   ```bash
   git checkout main
   git checkout -b hotfix/v1.0.1-security-patch
   ```
2. **Aplicar la corrección mínima:**
   - Escribir test de regresión que reproduzca la vulnerabilidad.
   - Aplicar el fix sin cambios cosméticos adicionales.
3. **Validar y Fusionar:**
   ```bash
   git checkout main
   git merge --no-ff hotfix/v1.0.1-security-patch -m "fix(security): emergency patch v1.0.1"
   git tag -a v1.0.1 -m "Hotfix v1.0.1: Parche de seguridad crítico"
   git push origin main --tags
   ```
4. **Propagar Inmediatamente a `develop`:**
   ```bash
   git checkout develop
   git merge --no-ff main -m "chore: backport hotfix v1.0.1 to develop"
   git push origin develop
   git branch -d hotfix/v1.0.1-security-patch
   ```

---

## 4. Trazabilidad de Cambios (Keep a Changelog)

El archivo `CHANGELOG.md` se actualiza obligatoriamente bajo las siguientes categorías canónicas:
- **`Added`**: Nuevas funcionalidades introducidas.
- **`Changed`**: Modificaciones en funcionalidades existentes.
- **`Deprecated`**: Funcionalidades que dejarán de estar soportadas en próximas versiones.
- **`Removed`**: Funcionalidades eliminadas.
- **`Fixed`**: Corrección de bugs o incidentes.
- **`Security`**: Mejoras de hardening o mitigación de vulnerabilidades.
