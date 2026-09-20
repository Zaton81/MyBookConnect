# Convención de Commits (Conventional Commits 1.0.0)

Este documento define el estándar oficial de mensajes de commit para **MyBookConnect**, basado en la especificación [Conventional Commits 1.0.0](https://www.conventionalcommits.org/es/v1.0.0/).

El cumplimiento estricto de este estándar permite mantener un historial de Git legible y estructurado, generar automáticamente las entradas de `CHANGELOG.md` y determinar de forma determinista el incremento de versión según SemVer 2.0.0.

---

## 1. Estructura General del Mensaje

Todo mensaje de commit debe seguir la siguiente estructura:

```text
<tipo>[ámbito opcional][!]: <descripción imperativa en presente>

[cuerpo opcional explicativo]

[pie(s) de página opcional(es)]
```

### Reglas básicas:
1. **Línea de cabecera (Header):**
   - Máximo 100 caracteres.
   - Todo el tipo y ámbito deben ir en **minúsculas**.
   - Espacio obligatorio tras los dos puntos (`: `).
   - Sin punto final en la descripción.
   - Redactado en modo imperativo presente (ej. *"añadir"* o *"add"*, no *"añadido"* ni *"added"*).
2. **Cuerpo (Body - Opcional):**
   - Separado de la cabecera por una línea en blanco.
   - Explica el *porqué* del cambio, no el *cómo*.
3. **Pie (Footer - Opcional):**
   - Referencias a issues (ej. `Closes #42`, `Fixes #108`) o alertas de cambio incompatible (`BREAKING CHANGE:`).

---

## 2. Tipos de Commit Permitidos

| Tipo | Propósito | Impacto SemVer | Mapeo en CHANGELOG.md |
| :--- | :--- | :--- | :--- |
| `feat` | Nueva característica o funcionalidad para el usuario. | MINOR (`0.X.0`) | `### Added` |
| `fix` | Corrección de un bug o error en funcionalidad existente. | PATCH (`0.0.X`) | `### Fixed` |
| `refactor` | Modificación de código que no añade funcionalidades ni arregla bugs (limpieza, modularización). | PATCH / Ninguno | `### Changed` |
| `perf` | Mejora de rendimiento o consumo de recursos (consultas SQL, caché, bundling). | PATCH | `### Changed` |
| `security` | Endurecimiento de seguridad, parche de vulnerabilidad, sanitización, rotación de secretos. | PATCH | `### Security` |
| `test` | Añadir o modificar pruebas (unitarias, integración, E2E, fixtures). | Ninguno | N/A |
| `docs` | Modificaciones exclusivas en documentación (`README.md`, `docs/`, docstrings). | Ninguno | N/A |
| `chore` | Tareas de mantenimiento, actualización de dependencias, scripts internos, tooling. | Ninguno | N/A |
| `ci` | Cambios en pipelines de integración continua (GitHub Actions, Docker Compose de CI). | Ninguno | N/A |
| `build` | Cambios que afectan al sistema de compilación o empaquetado (`pyproject.toml`, `vite.config.ts`). | Ninguno | N/A |
| `style` | Cambios de formato, espacios, linter o punto y coma que no afectan la lógica del código. | Ninguno | N/A |
| `revert` | Reversión de un commit previo. | Depende | `### Removed` / `### Changed` |

---

## 3. Ámbitos (Scopes) Reconocidos

El ámbito proporciona contexto modular inmediato sobre la zona del proyecto afectada:

```text
tipo(ámbito): descripción
```

| Ámbito | Componente o Módulo | Ejemplos |
| :--- | :--- | :--- |
| `(books)` | Catálogo de libros, autores, géneros, ISBN, portadas. | `feat(books): soportar busqueda por trigramas` |
| `(users)` | Perfiles de usuario, avatars, configuración, privacidad. | `fix(users): normalizar bio en perfiles publicos` |
| `(auth)` | Autenticación JWT, tokens, refresh, login, permisos. | `security(auth): revocar tokens en lista negra` |
| `(reviews)` | Reseñas, puntuaciones, likes, cálculo de promedios. | `fix(reviews): redondear media de valoraciones a 2 decimales` |
| `(chat)` | Mensajería directa, WebSockets, canales de Django Channels. | `feat(chat): scroll automatico al recibir nuevo mensaje` |
| `(gamification)` | Retos anuales, insignias (badges), metas de lectura. | `feat(gamification): anadir insignia por 50 libros leidos` |
| `(lists)` | Listas de lectura personalizadas y clubes. | `feat(lists): permitir reordenar libros en listas` |
| `(cache)` | Redis, invalidación de claves, decoradores, cache-aside. | `fix(cache): invalidar rankings en borrado de resena` |
| `(api)` | OpenAPI / Swagger, endpoints REST genéricos, paginación. | `docs(api): documentar respuestas 404 en /books/{id}/` |
| `(frontend)` | Componentes React, hooks, estado Zustand, TailwindCSS. | `refactor(frontend): migrar useAuth a Zustand store` |
| `(db)` | Modelos, índices PostgreSQL, migraciones, backup/restore. | `refactor(db): anadir indice compuesto en UserBook` |
| `(deps)` | Actualización de paquetes en `requirements.txt` o `package.json`. | `chore(deps): actualizar django a 5.2.17` |
| `(docker)` | Dockerfiles, `docker-compose.yml`, configuración de servicios. | `chore(docker): montar scripts y docs en backend` |
| `(ci)` | Flujos de GitHub Actions, linters automatizados. | `ci(github): anadir paso de verificacion de types` |
| `(release)` | Bumping de versión, preparación de CHANGELOG. | `chore(release): bump version to v1.0.0` |

---

## 4. Cambios Incompatibles (Breaking Changes)

Un commit que rompe la compatibilidad hacia atrás (**MAJOR**) debe señalarse de dos formas:

1. **Signo de exclamación `!`** inmediatamente antes de los dos puntos:
   ```text
   feat(api)!: cambiar estructura de respuesta en /api/v1/books/
   ```
2. **Pie de página `BREAKING CHANGE:`** explicando el cambio y la guía de migración:
   ```text
   feat(api)!: reestructurar payload de autenticacion

   BREAKING CHANGE: el endpoint /auth/token/ ahora devuelve 'access_token' en lugar de 'token'.
   ```

---

## 5. Ejemplos de Commits

### ✅ Commits Válidos:
```text
feat(books): anadir filtro por categorias y autores
fix(reviews): evitar votos duplicados en likes de resenas
refactor(services): separar logica de enriquecimiento asincrono
test(auth): anadir pruebas de rotacion de refresh tokens
docs: actualizar guia de despliegue en docker production
security(jwt): invalidar tokens con clave HMAC debil
perf(db): optimizar consulta de muro de actividad con select_related
chore(deps): bump vite de 5.0.0 a 6.4.3
feat(api)!: eliminar soporte para endpoints obsoletos /v0/
```

### ❌ Commits Inválidos:
| Mensaje Inválido | Causa del Rechazo |
| :--- | :--- |
| `arreglado el bug` | No incluye tipo válido ni dos puntos (`fix:`). |
| `Fix: arreglar bug` | El tipo debe ir estrictamente en minúsculas (`fix:`). |
| `feat:añadir libros` | Falta el espacio obligatorio después de los dos puntos. |
| `feat(libros): anadir libros.` | No debe terminar en punto (`.`). |
| `update: cambiar estilos` | `update` no es un tipo reconocido en la especificación. |
| `feat(books) anadir cosas` | Faltan los dos puntos separadores tras el scope. |

---

## 6. Instalación del Hook Local de Git (`commit-msg`)

Para validar tus mensajes de commit de forma automática antes de que se registren en tu historial local:

```bash
# Configurar Git para usar la carpeta de hooks del repositorio:
git config core.hooksPath .githooks
```

A partir de ese momento, cualquier `git commit` ejecutará el linter `scripts/validate_commit_msg.py` y rechazará mensajes que no cumplan el estándar.
