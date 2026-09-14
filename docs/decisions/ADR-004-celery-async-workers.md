# ADR-004: Procesamiento Asíncrono con Celery y Redis Broker

## Estado
Aceptado

## Contexto
Ciertas operaciones de la plataforma requieren llamadas a redes externas lentas o poco fiables (p. ej., descargar carátulas de libros desde OpenLibrary, consultar autores en Wikipedia o enriquecer metadatos con la API de Google Books). Ejecutar estas llamadas dentro del ciclo de petición HTTP bloquea los hilos de los servidores WSGI/ASGI y deteriora la experiencia del usuario.

## Decisión
Incorporar **Celery** con Redis como broker de mensajes para desacoplar todas las tareas no críticas del hilo principal de petición:
1. `download_cover_task`: descarga, valida y optimiza las portadas en formato WebP/JPEG de manera asíncrona.
2. `enrich_book_task`: consulta proveedores externos cuando un libro carece de sinopsis o autor.
3. `import_books_by_author_task`: busca obras adicionales de un autor en segundo plano.

## Consecuencias
### Positivas
- Tiempos de respuesta HTTP inmediatos sin penalización por latencias de APIs externas.
- Reintentos automáticos con retroceso exponencial (*exponential backoff*) ante fallos temporales de red.
- Capacidad de escalar trabajadores Celery de forma independiente del backend web.

### Negativas / Retos
- Requiere un proceso daemon adicional supervisado en Docker (`celery worker`).
- En entornos de test se activa `CELERY_TASK_ALWAYS_EAGER = True` para ejecución síncrona determinista.
