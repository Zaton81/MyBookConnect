# ADR-010: Topología de Contenedores de Producción Aislada y Nginx como Punto Único de Entrada

## Estado
Aceptado

## Contexto
En arquitecturas de microservicios o contenedores donde múltiples componentes (backend, base de datos, caché, workers) exponen puertos al host, se incrementa drásticamente la superficie de ataque y el riesgo de accesos no autorizados si falla una regla de firewall o se produce un error de configuración en la infraestructura.

## Decisión
Implementar en `docker-compose.prod.yml` una política estricta de aislamiento de red y privilegios mínimos:
1. **Punto Único de Entrada Perimetral:**
   - Nginx es el único servicio con mapeo de puertos hacia el host (`80:80` y `443:443`).
   - Todos los servicios internos (`backend`, `celery_worker`, `db`, `cache`) carecen de directiva `ports` y solo interactúan a través de redes Docker bridge dedicadas.
2. **Segmentación de Redes Internas:**
   - Red `frontend_net`: Conecta Nginx con el frontend estático y el backend ASGI/Daphne.
   - Red `backend_net`: Conecta backend, Celery, PostgreSQL y Redis, marcada con `internal: true` para bloquear cualquier tráfico entrante o saliente con el exterior no autorizado.
3. **Usuarios No-Root:**
   - Todos los contenedores de aplicación ejecutan procesos bajo usuarios sin privilegios (`uid: 1000:1000` / `booksocial`).
4. **Límites de Recursos y Ciclo de Vida:**
   - Cuotas fijas de CPU y memoria (`deploy.resources.limits`) para mitigar ataques DoS.
   - `stop_grace_period` y `stop_signal` diferenciados para parada ordenada sin pérdida de transacciones ni tareas Celery en vuelo.

## Consecuencias
### Positivas
- Reducción total de la superficie de ataque perimetral: PostgreSQL y Redis son inaccesibles desde internet.
- Aislamiento en caso de compromiso de un contenedor web (no puede saltar a redes de administración).
- Prevención de monopolio de recursos o caídas en cascada mediante límites Docker.

### Negativas / Retos
- El mantenimiento administrativo directo (ej. `psql` manual) requiere el uso de `docker compose exec` o túneles de bastión controlados.
