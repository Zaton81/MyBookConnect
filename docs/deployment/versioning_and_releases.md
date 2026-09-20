# Guía de Versionado y Proceso de Releases

Esta guía documenta la política de versiones y el procedimiento estandarizado para la publicación de releases en **MyBookConnect**.

---

## 1. Esquema de Versionado (SemVer 2.0.0)

MyBookConnect implementa estrictamente [Semantic Versioning 2.0.0](https://semver.org/lang/es/):

Formato: `MAJOR.MINOR.PATCH` (ej. `1.0.0`)

- **MAJOR (Mayor)**: Cambios incompatibles en la API pública (breaking changes), reestructuraciones de modelos o esquemas no retrocompatibles.
- **MINOR (Menor)**: Nuevas funcionalidades compatibles hacia atrás (ej. nuevos endpoints, nuevos modelos, soporte de nuevas características).
- **PATCH (Parche)**: Correcciones de errores y bugs compatibles hacia atrás, mejoras de rendimiento o parches de seguridad.
- **Etiquetas de Pre-release**: Opcionalmente `-rc1`, `-beta`, etc., para versiones de prueba antes de la salida definitiva.

---

## 2. Puntos Únicos de Verdad de la Versión

Para garantizar consistencia en todo el ecosistema, la versión debe mantenerse sincronizada en:

1. **Backend Python**:
   - `backend/mybookconnect/version.py`: Define `VERSION = (1, 0, 0)` y expone `get_version()`, `get_version_info()`.
   - `backend/mybookconnect/__init__.py`: Exporta `__version__ = get_version()`.
   - `backend/pyproject.toml`: Sección `[project]` con `version = "1.0.0"`.
2. **Frontend SPA**:
   - `frontend/package.json`: Campo `"version": "1.0.0"`.
3. **Registro de Cambios**:
   - `CHANGELOG.md`: Entrada documentada bajo `## [X.Y.Z] - YYYY-MM-DD` siguiendo *Keep a Changelog 1.1.0*.
4. **Git**:
   - Tag anotado de Git: `vX.Y.Z` (ej. `v1.0.0`).

---

## 3. Endpoints de Versión en la API

- **Endpoint de versión dedicado**:
  - `GET /api/v1/version/`
  - Respuesta HTTP 200 OK:
    ```json
    {
      "version": "1.0.0",
      "major": 1,
      "minor": 0,
      "patch": 0,
      "prerelease": null,
      "api_version": "v1",
      "semver": true
    }
    ```
- **Endpoint de salud (Liveness)**:
  - `GET /api/v1/health/`
  - Incluye el campo `"version": "1.0.0"`.

---

## 4. Estándar de CHANGELOG (Keep a Changelog 1.1.0)

Todo cambio significativo debe clasificarse bajo las categorías estándar:
- `Added`: Nuevas características.
- `Changed`: Cambios en la funcionalidad existente.
- `Deprecated`: Funcionalidades que se eliminarán en futuras versiones.
- `Removed`: Funcionalidades eliminadas.
- `Fixed`: Corrección de errores.
- `Security`: Parches y endurecimientos de seguridad.

---

## 5. Script de Verificación de Release

Antes de taggear y desplegar cualquier release, se debe ejecutar:

```bash
bash scripts/verify_release.sh
```

El script valida:
1. Coherencia de versiones entre `backend/mybookconnect/version.py`, `backend/pyproject.toml` y `frontend/package.json`.
2. Existencia de la entrada correspondiente en `CHANGELOG.md`.
3. Ejecución y paso sin errores de las pruebas unitarias y de integración.
4. Linters y tipado limpios.

---

## 6. Procedimiento de Publicación (Release Workflow)

1. Crear una rama de release desde `develop`:
   ```bash
   git checkout -b release/v1.0.0 develop
   ```
2. Actualizar las versiones en `backend/mybookconnect/version.py`, `backend/pyproject.toml` y `frontend/package.json`.
3. Mover los cambios relevantes de `[Unreleased]` a `[1.0.0] - YYYY-MM-DD` en `CHANGELOG.md`.
4. Ejecutar el script de verificación:
   ```bash
   bash scripts/verify_release.sh
   ```
5. Realizar commit del release:
   ```bash
   git commit -m "chore(release): bump version to v1.0.0"
   ```
6. Fusionar en `main` y crear el tag anotado:
   ```bash
   git checkout main
   git merge --no-ff release/v1.0.0
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin main --tags
   ```
7. Fusionar de vuelta en `develop`:
   ```bash
   git checkout develop
   git merge --no-ff release/v1.0.0
   git push origin develop
   git branch -d release/v1.0.0
   ```
