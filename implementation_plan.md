# Plan de Implementación — RoadmapV3: Sprint 4 (Catálogo, Deduplicación de Ediciones y Búsqueda Unificada — P1)

**Fecha:** 3 de octubre de 2026  
**Rama de trabajo:** `develop`  
**Estado:** Propuesto para revisión y aprobación  
**Prioridad:** P1 (Catálogo, Integridad Editorial y Experiencia de Descubrimiento)

---

## 1. Contexto y Requisitos del Usuario

El usuario ha especificado una directiva central para el catálogo:
> *"todos los libros de un mismo autor y mismo nombre, deben quedar unificados. Es decir, si hay físico y digital a veces tienen distinto isbn, pero el libro es el mismo"*.

Esto se alinea con la **Sección 5 (Catálogo y libros)** y la **Sección 9 (Búsqueda y descubrimiento)** de `RoadmapV3.md`.

### Objetivos Principales:
1. **Unificación de Ediciones de un Mismo Libro (Físico / Digital / Distintos ISBNs):**
   - Una única ficha canónica por obra (`Book`) cuando compartan autor (o variantes canónicas) y título normalizado (insensible a mayúsculas, tildes, signos de puntuación o espacios).
   - Soporte para almacenar y consultar múltiples ISBNs por libro mediante `additional_isbns` (lista JSON de ISBNs normalizados asociados a la obra: físico, ebook/digital, bolsillo, etc.).
   - Capacidad de encontrar la obra unificada buscando por **cualquiera** de sus ISBNs (el principal o cualquiera de los alternativos).

2. **Servicio y Herramienta de Fusión y Deduplicación (`BookDeduplicationService`):**
   - Detección automática de duplicados existentes en el catálogo.
   - Fusión transaccional segura hacia el libro canónico:
     - Reasignación de `UserBook` (biblioteca de usuarios), resolviendo colisiones si el usuario tenía ambos formatos (preservando el estado más avanzado y la mejor calificación).
     - Reasignación de `Review` (reseñas), `ReadingListBook` (listas de lectura), citas y reportes de erratas.
     - Consolidación de categorías, portadas, descripciones y todos los ISBNs asociados.
     - Eliminación limpia de las instancias duplicadas redundantes.
   - Comando de gestión Django: `python manage.py deduplicate_catalog [--dry-run]`.

3. **Blindaje en la Ingesta / Creación de Libros:**
   - En `BookSerializer`: si un usuario o cliente intenta crear un libro que ya existe para ese autor y título, no se crea un duplicado; se enriquece el libro existente (incorporando el nuevo ISBN a `additional_isbns` si procede) y se retorna el libro canónico.
   - En los servicios de importación externa (`import_service.py` y `csv_import_service.py`): la resolución comprueba tanto ISBN principal y alternativos como la tupla (título normalizado, autor), fusionando inmediatamente cualquier edición entrante con la ficha existente.

4. **Búsqueda Global Unificada (`/api/v1/search/?q=...`):**
   - Endpoint unificado que devuelve en una sola llamada los resultados categorizados en:
     - `books`: libros que coincidan por título, autor, descripción o cualquiera de sus ISBNs.
     - `authors`: autores que coincidan por nombre o alias, con sus métricas.
     - `users`: usuarios públicos (respetando bloqueos y privacidad).
   - Interfaz en el frontend para búsqueda global `/search?q=...` con selector de pestañas (Todo, Libros, Autores, Lectores).

---

## 2. Modificaciones Técnicas Propuestas

### 2.1. Modelo `Book` (`backend/books/models.py`)
- Añadir campo `additional_isbns = models.JSONField(default=list, blank=True, help_text="Listado de ISBNs adicionales/alternativos (ediciones físicas, digitales, etc.)")`.
- Crear función auxiliar de normalización de títulos `normalize_title(title: str) -> str` (remueve puntuación superflua, dobles espacios y acentos para comparación canónica).
- Crear método `add_isbn(isbn: str)` en `Book` que normalice e inserte en `additional_isbns` evitando duplicados.
- Crear método de clase `Book.find_by_isbn(isbn: str)` que busque tanto en `isbn` como en `additional_isbns`.
- Crear migración de Django correspondiente.

### 2.2. Servicio de Deduplicación y Fusión (`backend/books/services/deduplication_service.py`)
- `find_duplicate_books() -> list[tuple[Book, list[Book]]]`:
  - Agrupa libros por `(author_id, normalized_title)`.
- `merge_books(canonical_book: Book, duplicate_books: list[Book]) -> Book`:
  - Ejecuta la fusión en una transacción atómica `transaction.atomic()`:
    1. Acumula todos los ISBNs secundarios en `canonical_book.additional_isbns`.
    2. Si el canónico no tiene portada o descripción pero un duplicado sí, los transfiere.
    3. Fusiona categorías M2M.
    4. Migra `UserBook`: si el usuario ya tenía el canónico, actualiza con el estado más avanzado; si no, reasigna el `book_id`.
    5. Migra `Review`: reasigna al canónico evitando duplicar reseñas del mismo usuario en la misma obra.
    6. Migra `ReadingListBook`: reasigna elementos de listas sociales evitando duplicados en la misma lista.
    7. Elimina los registros `duplicate_books`.
- Comando `backend/books/management/commands/deduplicate_catalog.py` para ejecución manual o en cron/worker.

### 2.3. Blindaje de Creación e Importación
- En `backend/books/serializers.py` (`BookSerializer.create`):
  - Normaliza el título y comprueba si ya existe un libro con ese autor y título. Si existe, agrega el ISBN a `additional_isbns` y devuelve el libro canónico.
- En `backend/books/services/import_service.py` y `csv_import_service.py`:
  - Buscar primero por ISBN (en `isbn` y `additional_isbns`).
  - Si no se encuentra por ISBN, buscar por `(author, normalized_title)`.
  - Si existe por título y autor pero con otro ISBN, registrar el nuevo ISBN en `additional_isbns` del libro existente en lugar de crear un libro nuevo.

### 2.4. Búsqueda Global Unificada (`/api/v1/search/?q=...`)
- Crear `GlobalSearchView` en `backend/books/views.py` expuesta en `/api/v1/search/`:
  - Parámetros: `q` (término), `type` (opcional: `all`, `books`, `authors`, `users`), `limit`.
  - Libros: búsqueda híbrida / trigram (`pg_trgm`) por título, autor y match en `isbn` / `additional_isbns`.
  - Autores: búsqueda por nombre canónico y aliases (`idx_author_name_trgm`).
  - Usuarios: búsqueda por `username`, aplicando `PrivacyService` y exclusión de usuarios bloqueados/bloqueadores.
- En frontend:
  - Componente/página `SearchPage.tsx` accesible en `/search?q=...`.
  - Pestañas interactivas: "Todos", "Libros", "Autores", "Lectores".

---

## 3. Plan de Pruebas y Validación

1. **Pruebas Unitarias y de Integración (`backend/tests/test_sprint4_catalog_deduplication.py`):**
   - Test de unificación: crear un libro físico y un libro digital del mismo autor y título con distintos ISBNs; comprobar que quedan unificados bajo una sola ficha con ambos ISBNs registrados.
   - Test de búsqueda por ISBN alternativo: verificar que buscar por el ISBN del ebook devuelve la ficha del libro unificado.
   - Test de fusión transaccional (`merge_books`): verificar que estanterías (`UserBook`), reseñas (`Review`) y listas (`ReadingList`) se transfieren íntegramente sin errores de integridad.
   - Test de búsqueda global unificada (`/api/v1/search/?q=...`): comprobar que devuelve simultáneamente libros, autores y lectores respetando la privacidad.
2. **Pruebas de Regresión Completa:**
   - Ejecutar secuencialmente Sprints 1, 2, 3 y 4:
     `pytest tests/test_sprint1_security.py tests/test_sprint2_infrastructure.py tests/test_sprint3_authors_and_faqs.py tests/test_sprint4_catalog_deduplication.py`
3. **Build de Frontend:**
   - `npm run build` en `frontend/` verificando compilación limpia.

---

## 4. Criterios de Aceptación (Definition of Done)

- [ ] Libros con el mismo autor y mismo título quedan estrictamente unificados en una sola entidad `Book`.
- [ ] Los distintos ISBNs (físico, digital, tapa dura) se almacenan en `additional_isbns` y son buscables.
- [ ] Servicio de deduplicación y comando CLI `deduplicate_catalog` operativos y probados.
- [ ] Endpoint `/api/v1/search/?q=...` devuelve resultados clasificados de libros, autores y lectores.
- [ ] 100% tests pasando secuencialmente sin bloqueos de base de datos.
- [ ] Documentación actualizada (`RoadmapV3.md`, `memory.md`, `CHANGELOG.md`).
- [ ] Commit semántico y push a `develop`.
