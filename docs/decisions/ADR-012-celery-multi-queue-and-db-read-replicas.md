# ADR-012: Enrutamiento Celery Multi-Cola y Arquitectura de Réplicas de Lectura en Base de Datos

## Estado
Aceptado

## Contexto
El aumento en la concurrencia de lectura (catálogo y búsquedas) y la heterogeneidad de tareas asíncronas en segundo plano (desde envíos rápidos de correo transaccional hasta inferencias de IA, generación de TTS y extracción de embeddings) provocaba cuellos de botella en la cola por defecto (`default`) y saturación del nodo primario de base de datos.

## Decisión
1. **Topología de 5 Colas Celery Aisladas:**
   - Se segmenta el procesamiento en 5 colas explícitas mediante `CELERY_TASK_ROUTES`:
     - `emails`: Notificaciones transaccionales y digests (prioridad alta, latencia baja).
     - `books`: Sincronización de catálogos, PA-API, extracción de metadatos e ISBNs.
     - `recommendations`: Recálculo de afinidades literarias y clustering comunitario.
     - `ai`: Inferencia de resúmenes, síntesis multimodal y embeddings vectoriales.
     - `default`: Tareas del sistema, limpieza y telemetría.
   - En desarrollo/staging un único worker escucha todas las colas (`-Q default,books,ai,recommendations,emails`), permitiendo en producción escalar workers dedicados horizontalmente para colas pesadas sin bloquear tareas ligeras.
2. **Router Primario / Réplica (`PrimaryReplicaRouter`):**
   - Implementado en `backend/mybookconnect/db_routers.py`.
   - Las lecturas (`db_for_read`) se enrutan a la base de datos `replica` si está definida en `DATABASES`. Si no existe, recurre de forma transparente a `default`.
   - Todas las escrituras (`db_for_write`) se dirigen exclusivamente a `default` (nodo primario).
   - Bloqueo explícito de migraciones (`allow_migrate`) en nodos de sólo lectura para garantizar consistencia del esquema.
3. **Balanceo Nginx con `least_conn`:**
   - El grupo upstream `django_cluster` distribuye el tráfico utilizando el algoritmo de conexiones mínimas (`least_conn`) para evitar sobrecargar workers ocupados con peticiones largas de streaming o IA.

## Consecuencias
### Positivas
- Aislamiento completo: tareas pesadas de IA o enriquecimiento de libros nunca retrasan el envío de correos de activación de cuenta o restablecimiento de contraseña.
- Capacidad de descargar hasta el 80% del tráfico SQL de lectura hacia réplicas de sólo lectura de PostgreSQL.
- Elasticidad operativa e independencia de escalado horizontal.

### Negativas / Retos
- Requiere contemplar el retraso eventual de replicación (replication lag) en flujos de lectura inmediata tras escritura ("read-your-own-writes").
