# Guía Definitiva de Resolución de Problemas y Runbooks para Desarrolladores

Esta guía recopila los procedimientos estandarizados, diagnósticos y soluciones paso a paso para resolver las incidencias más frecuentes durante el desarrollo, despliegue y mantenimiento de **MyBookConnect**.

---

## Índice de Contenidos
1. [Problemas de Git y Control de Versiones](#1-problemas-de-git-y-control-de-versiones)
2. [Problemas de Docker y Entorno de Contenedores](#2-problemas-de-docker-y-entorno-de-contenedores)
3. [Problemas de Base de Datos PostgreSQL y Migraciones Django](#3-problemas-de-base-de-datos-postgresql-y-migraciones-django)
4. [Problemas de Redis, Caché y Tareas Asíncronas Celery](#4-problemas-de-redis-caché-y-tareas-asíncronas-celery)
5. [Problemas de Frontend (React, Vite, TypeScript)](#5-problemas-de-frontend-react-vite-typescript)
6. [Runbook de Diagnóstico Rápido del Sistema](#6-runbook-de-diagnóstico-rápido-del-sistema)

---

## 1. Problemas de Git y Control de Versiones

### 1.1. Conflictos durante un Merge o Rebase
**Síntoma:** Git detiene la operación e informa de archivos en conflicto con marcadores `<<<<<<<`, `=======`, `>>>>>>>`.

**Solución paso a paso:**
1. Ver qué archivos tienen conflictos:
   ```bash
   git status
   ```
2. Abrir cada archivo conflictivo en el editor, localizar los marcadores de conflicto y decidir el código final deseado.
3. Marcar los archivos resueltos:
   ```bash
   git add <archivo-resuelto>
   ```
4. Continuar la operación:
   - Si estabas en un **merge**:
     ```bash
     git commit -m "merge: resolver conflictos con develop"
     ```
   - Si estabas en un **rebase**:
     ```bash
     git rebase --continue
     ```
5. **Si necesitas abortar sin alterar nada:**
   ```bash
   git merge --abort    # Para abortar un merge
   git rebase --abort   # Para abortar un rebase
   ```

---

### 1.2. Rechazo de Push por Desincronización (`non-fast-forward`)
**Síntoma:** Al hacer `git push origin mi-rama`, Git responde: `[rejected - non-fast-forward] Updates were rejected because the remote contains work that you do not have locally`.

> [!CAUTION]
> **Nunca** uses `git push --force` a menos que sea una rama de trabajo personal aislada y conozcas exactamente las consecuencias. Está prohibido en `develop` y `main`.

**Solución recomendada:**
```bash
# 1. Obtener los últimos commits del remoto sin mezclar a ciegas
git fetch origin

# 2. Rebasar tus commits locales sobre la rama remota actualizada
git rebase origin/mi-rama

# 3. Si surgen conflictos, resuélvelos y haz git rebase --continue
# 4. Empujar tus cambios limpiamente:
git push origin mi-rama
```

---

### 1.3. Salir del estado "Detached HEAD"
**Síntoma:** El prompt de Git muestra `HEAD detached at <commit-sha>`. Los commits que hagas aquí se perderán al cambiar de rama.

**Solución paso a paso:**
```bash
# 1. Crear una rama temporal que conserve los commits realizados en este estado:
git branch rescate-cambios

# 2. Volver a tu rama de trabajo legítima:
git checkout develop

# 3. Incorporar los commits rescatados:
git merge rescate-cambios

# 4. Eliminar la rama temporal:
git branch -d rescate-cambios
```

---

### 1.4. Deshacer cambios sin romper el historial
Dependiendo del tipo de cambio que necesites deshacer:

| Caso de uso | Comando recomendado | Efecto |
| :--- | :--- | :--- |
| Descartar modificaciones locales sin commitear en un archivo | `git restore <archivo>` | Restaura el archivo a la versión del último commit. |
| Descartar todos los cambios locales sin commitear | `git restore .` | Limpia el working tree sin tocar commits. |
| Deshacer el último commit manteniendo los cambios en staging | `git reset --soft HEAD~1` | Permite corregir el mensaje o contenido del commit. |
| Deshacer un commit que ya fue subido a GitHub | `git revert <commit-sha>` | Crea un nuevo commit que invierte los cambios de forma segura. |
| Descartar completamente el último commit y sus archivos | `git reset --hard HEAD~1` | ⚠️ Destructivo: elimina los cambios permanentemente. |

---

### 1.5. Rescate de commits o ramas borradas accidentalmente (`git reflog`)
**Síntoma:** Borraste una rama o ejecutaste un `git reset --hard` no deseado y perdiste horas de trabajo.

**Solución:**
```bash
# 1. Consultar el registro de todas las posiciones del puntero HEAD:
git reflog

# 2. Localizar el hash SHA o la entrada HEAD@{N} previa al desastre (ej. HEAD@{3})
# 3. Crear una nueva rama basada en ese punto exacto:
git branch rama-recuperada HEAD@{3}

# 4. Cambiar a la rama recuperada:
git checkout rama-recuperada
```

---

### 1.6. Gestión segura de cambios en curso con `git stash`
Cuando necesitas cambiar de rama con urgencia sin commitear trabajo a medio terminar:

```bash
# 1. Guardar cambios en el stash con un mensaje descriptivo:
git stash push -m "WIP: trabajo a medias en filtros de busqueda"

# 2. Cambiar de rama y realizar las tareas necesarias:
git checkout develop

# 3. Al volver a tu rama, restaurar los cambios guardados:
git stash list          # Muestra el historial de stashes (ej. stash@{0})
git stash pop           # Aplica el último stash y lo elimina de la lista
# O si prefieres mantenerlo por seguridad:
git stash apply
```

---

### 1.7. Commit realizado por error en la rama equivocada
**Escenario:** Hiciste 1 o varios commits en `develop` cuando debían estar en una rama `feature/mi-tarea`.

**Solución:**
```bash
# 1. Crear la nueva rama donde debían estar los commits:
git branch feature/mi-tarea

# 2. Estando en develop, retroceder los commits equivocados (ej. 1 commit):
git reset --hard HEAD~1

# 3. Cambiar a la rama correcta (tendrá todos tus commits intactos):
git checkout feature/mi-tarea
```

---

### 1.8. Advertencias de finales de línea Windows / Linux (CRLF vs LF)
**Síntoma:** Mensajes constantes de Git como: `warning: in the working copy of '...', LF will be replaced by CRLF the next time Git touches it`.

**Solución recomendada:**
Configurar Git para convertir automáticamente CRLF a LF al commitear:
```bash
git config --global core.autocrlf true   # En Windows
# O a nivel de repositorio:
git config core.autocrlf true
```

---

## 2. Problemas de Docker y Entorno de Contenedores

### 2.1. Puertos en Conflicto (`Address already in use`)
**Síntoma:** Al levantar el stack, Docker muestra: `Bind for 0.0.0.0:8000 failed: port is already allocated`.

**Diagnóstico y solución:**
- **Identificar el proceso que ocupa el puerto:**
  - En Windows (PowerShell):
    ```powershell
    Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
    Stop-Process -Id <PID> -Force
    ```
  - En Linux / WSL:
    ```bash
    sudo lsof -i :8000
    sudo kill -9 <PID>
    ```
- **Contenedores huérfanos de Docker:**
  ```bash
  docker compose down --remove-orphans
  ```

---

### 2.2. Contenedor en Bucle de Reinicio (*CrashLoopBackOff*)
**Síntoma:** El contenedor del backend o de postgres se reinicia continuamente.

**Diagnóstico:**
```bash
# 1. Ver los últimos logs del contenedor específico:
docker compose logs --tail=100 backend

# 2. Si el contenedor se cae al instante, inspeccionar el código de salida:
docker ps -a --filter "name=booksocial"
```

**Causas habituales y solución:**
1. **Error de sintaxis en Python:** el log mostrará el traceback exacto. Corregir y guardar el archivo (el backend recarga en caliente).
2. **PostgreSQL no listo:** el backend intenta arrancar antes de que la BD acepte conexiones. Comprobar que el servicio `db` tenga el healthcheck configurado en `docker-compose.yml`.

---

### 2.3. Acceso Interactivo a un Contenedor
Para depurar directamente dentro de los entornos:
```bash
# Backend Django:
docker compose exec -it backend bash

# PostgreSQL:
docker compose exec -it db psql -U booksocial -d booksocial

# Redis:
docker compose exec -it redis redis-cli
```

---

### 2.4. Limpieza Total y Reconstrucción Limpia del Entorno
Cuando el entorno local queda en un estado inconsistente de volúmenes o imágenes corruptas:

> [!WARNING]
> La opción `-v` eliminará los volúmenes de datos locales de PostgreSQL y Redis. Asegúrate de tener backups si los datos son críticos.

```bash
# 1. Detener y purgar contenedores, redes y volúmenes:
docker compose down -v --remove-orphans

# 2. Reconstruir imágenes desde cero sin usar caché:
docker compose build --no-cache

# 3. Levantar los servicios en segundo plano:
docker compose up -d

# 4. Aplicar migraciones:
docker compose exec backend python manage.py migrate
```

---

## 3. Problemas de Base de Datos PostgreSQL y Migraciones Django

### 3.1. Conflictos de Migraciones Inconsistentes (`InconsistentMigrationHistory`)
**Síntoma:** Django arroja: `django.db.migrations.exceptions.InconsistentMigrationHistory`.

**Causa:** Se aplicaron migraciones que dependen de una migración que aún no figura como aplicada en la tabla `django_migrations`.

**Solución:**
1. Comprobar el estado actual de todas las migraciones:
   ```bash
   docker compose exec backend python manage.py showmigrations
   ```
2. Si dos ramas crearon números de migración idénticos con nombres distintos (ej. `0015_add_tags` y `0015_add_likes`):
   - Fusionar las cabeceras conflictivas de Django:
     ```bash
     docker compose exec backend python manage.py makemigrations --merge
     ```
   - Aplicar las migraciones:
     ```bash
     docker compose exec backend python manage.py migrate
     ```

---

### 3.2. Revertir una Migración Problemática
Si una migración recién aplicada causó un fallo y necesitas desaplicarla:

```bash
# Revertir la app 'books' hasta la migración 0014:
docker compose exec backend python manage.py migrate books 0014

# Si deseas desaplicar TODAS las migraciones de una app:
docker compose exec backend python manage.py migrate books zero
```

---

### 3.3. Bloqueo de Transacciones y Conexiones Colgadas (*Deadlocks*)
**Síntoma:** Las peticiones a la API quedan bloqueadas indefinidamente esperando a la base de datos.

**Diagnóstico y solución:**
1. Abrir la terminal interactiva de PostgreSQL:
   ```bash
   docker compose exec db psql -U booksocial -d booksocial
   ```
2. Listar transacciones activas o bloqueadas:
   ```sql
   SELECT pid, age(clock_timestamp(), query_start), usename, state, query 
   FROM pg_stat_activity 
   WHERE state != 'idle' AND query NOT ILIKE '%pg_stat_activity%';
   ```
3. Terminar una consulta bloqueante por su PID:
   ```sql
   SELECT pg_terminate_backend(<PID>);
   ```

---

### 3.4. Restaurar la Base de Datos desde el Último Backup
Para volver a un punto seguro de datos tras una corrupción de pruebas:
```bash
docker compose exec backend python manage.py restore_db
```

---

## 4. Problemas de Redis, Caché y Tareas Asíncronas Celery

### 4.1. Desincronización o Corrupción de Caché
**Síntoma:** La API devuelve datos desactualizados o inconsistentes a pesar de haber modificado registros en la base de datos.

**Solución inmediata (Principio: Redis NO es fuente de verdad):**
1. Vaciar la caché volátil de Redis:
   ```bash
   docker compose exec redis redis-cli FLUSHALL
   ```
2. Reconstruir deterministamente los rankings de tendencias y precalentar el catálogo:
   ```bash
   docker compose exec backend python manage.py rebuild_cache --limit 100
   ```

---

### 4.2. Colas de Celery Congeladas o Acumulación Masiva de Tareas
**Síntoma:** Las tareas en segundo plano (descarga de portadas, enriquecimiento de libros) no se ejecutan y se quedan encoladas.

**Solución:**
1. Verificar si el worker de Celery está activo:
   ```bash
   docker compose logs -f celery_worker
   ```
2. Purgar todas las tareas pendientes acumuladas en la cola:
   ```bash
   docker compose exec backend celery -A mybookconnect purge -f
   ```
3. Reiniciar el contenedor de Celery:
   ```bash
   docker compose restart celery_worker
   ```

---

### 4.3. Problemas con WebSockets y Django Channels
**Síntoma:** El chat en vivo no conecta o se desconecta con código `1006` en el navegador.

**Diagnóstico:**
1. Verificar que Redis Channel Layer responde pings:
   ```bash
   docker compose exec redis redis-cli ping
   # Debe responder: PONG
   ```
2. Verificar que el backend corre con Daphne (ASGI) y no con WSGI estándar.

---

## 5. Problemas de Frontend (React, Vite, TypeScript)

### 5.1. Fallos de Caché de Vite o Pantalla en Blanco en Desarrollo
**Síntoma:** Cambios en el código no se reflejan, o la consola muestra errores de importación de módulos pre-bundling.

**Solución:**
```bash
# Limpiar la caché de optimización de dependencias de Vite:
rm -rf frontend/node_modules/.vite
# Reiniciar el servidor de desarrollo:
npm --prefix frontend run dev
```

---

### 5.2. Dependencias Inconsistentes o Módulos Faltantes
**Síntoma:** `Cannot find module '@tanstack/react-query'` o errores al resolver paquetes.

**Solución:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run typecheck
```

---

### 5.3. Errores de Tipos TypeScript (`tsc --noEmit`)
Para comprobar rápidamente todos los errores de tipado sin compilar artefactos:
```bash
npm --prefix frontend run typecheck
```
Si los tipos de la API cambiaron en el backend, regenerar los tipos OpenAPI:
```bash
npm --prefix frontend run generate:types
```

---

## 6. Runbook de Diagnóstico Rápido del Sistema

Para evaluar en menos de 10 segundos el estado general del entorno de desarrollo:

```bash
bash scripts/doctor.sh
```

El script valida automáticamente:
- Estado del árbol de trabajo Git y sincronización con el remoto.
- Contenedores Docker levantados (`backend`, `db`, `redis`, `celery_worker`).
- Conectividad a PostgreSQL y Redis.
- Existencia de migraciones pendientes de aplicar.
- Sincronización de versiones SemVer en backend y frontend.
- Endpoints de salud HTTP (`/api/v1/health/`, `/api/v1/ready/`, `/api/v1/version/`).
