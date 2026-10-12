# Informe Técnico de Carga y Cumplimiento de SLAs (Fase B4)

Este documento certifica la auditoría de rendimiento, escalabilidad básica y cumplimiento de **SLAs de latencia (p95 / p99)** en **MyBookConnect** (**Fase B4 — Roadmap v2.0**).

---

## 1. Definición Formal de SLAs y Presupuestos de Rendimiento

| Endpoint / Componente | SLA p95 Objetivo | SLA p99 Objetivo | Complejidad / Dependencias | Tipo de Operación |
| :--- | :--- | :--- | :--- | :--- |
| **Sonda Liveness (`/health/live`)** | $\le 100$ ms | $\le 200$ ms | $O(1)$ — Autónomo sin dependencias | Monitoreo K8s / Docker |
| **Sonda Readiness (`/health/ready`)** | $\le 150$ ms | $\le 300$ ms | $O(1)$ — PostgreSQL ping + Redis ping | Despliegue y tráfico |
| **Catálogo General (`/api/v1/books/`)** | $\le 300$ ms | $\le 600$ ms | $O(N)$ con paginación e índices compuestos | Lectura pública |
| **Descubrimiento y Tendencias (`/api/v1/books/discover/`)**| $\le 500$ ms | $\le 1000$ ms | Caché Redis L2 + filtrado multi-género | Lectura intensiva |
| **Búsqueda Trigram / Semántica (`/api/v1/search/`)** | $\le 500$ ms | $\le 1200$ ms | GIN trgm + embeddings pgvector | Consulta computacional |

---

## 2. Metodología de Prueba de Carga

La evaluación se ejecuta mediante el script automatizado de benchmarking:
```bash
python scripts/load_testing/load_test_benchmark.py --host http://localhost:8000 --concurrency 10 --requests 50 --output-json ./reports/sla_report.json
```

### Condiciones de la Prueba:
- **Concurrencia:** 10 hilos simultáneos generando peticiones asíncronas sobre el reverse proxy.
- **Volumen:** Lotes de 50 peticiones por endpoint (200 peticiones acumuladas por ciclo).
- **Métricas registradas:** Tasa de éxito (%), RPS (peticiones/segundo), latencia media, percentil p50, percentil p95 y percentil p99.

---

## 3. Arquitectura de Escalabilidad Horizontal

### A. Balanceo de Carga Nginx (`upstream django_cluster`)
- Nginx actúa como API Gateway y distribuidor de carga mediante algoritmo `least_conn`.
- Las peticiones se distribuyen de forma balanceada entre los procesos Daphne activos:
```nginx
upstream django_cluster {
    least_conn;
    server backend:8000 max_fails=3 fail_timeout=10s;
}
```

### B. Escalado de Contenedores de Aplicación
Para escalar los workers del backend en entornos de alta concurrencia:
```bash
# Escalar a 2 réplicas del contenedor de backend
docker compose -f docker-compose.prod.yml up -d --scale backend=2
```

### C. Réplicas de Lectura en PostgreSQL (`PrimaryReplicaRouter`)
- El router de base de datos segrega de forma determinista el tráfico:
  - **Escrituras:** Dirigidas exclusivamente al nodo maestro (`default`).
  - **Lecturas:** Si existe una réplica configurada en `settings.DATABASES['replica']`, las consultas de lectura se derivan a la réplica, aliviando la carga del primario.
  - **Fallback:** En ausencia de réplica, todas las lecturas se ejecutan en `default` sin degradación funcional.

### D. Aislamiento en 5 Colas Especializadas Celery
Las tareas pesadas nunca compiten con el tráfico síncrono del usuario:
1. `default`: Registro de analíticas y eventos de auditoría.
2. `books`: Enriquecimiento de metadatos, recálculo atómico de ratings y portadas.
3. `ai`: Generación de embeddings vectoriales.
4. `recommendations`: Precomputación asíncrona periódica de afinidad.
5. `emails`: Envío de notificaciones y confirmaciones transaccionales.

---

## 4. Estrategia de Caché L2 e Invalidación Reactiva

- **Capa L1 (Memoria de proceso):** Conexiones y metadatos estáticos.
- **Capa L2 (Redis):** Caché distribuida de alta velocidad:
  - Claves de catálogo y detalle (`book:detail:{id}`).
  - Listas de tendencias multi-período (`trending:week`, `trending:month`, `trending:year`, `trending:all`).
  - Recomendaciones personalizadas de usuarios.
- **Invalidación en Cascada:** Cuando se publica o actualiza una reseña (`cascade_review_invalidation`), se purga de forma reactiva la caché del libro, los rankings de tendencias y las recomendaciones dependientes.
