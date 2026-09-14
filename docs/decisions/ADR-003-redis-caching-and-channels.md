# ADR-003: Estrategia de Caché y Capa de Canales con Redis

## Estado
Aceptado

## Contexto
El rendimiento de la plataforma depende de servir rápidamente peticiones de lectura frecuentes (detalles de libros populares, catálogos, recomendaciones) y de posibilitar la mensajería instantánea distribuida entre los usuarios sin sobrecargar PostgreSQL.

## Decisión
Utilizar **Redis 7+** para desempeñar múltiples roles clave en la infraestructura:
1. **Caché en Memoria:** Almacenamiento clave-valor con prefijo de nombres (`mbc:` o `book:`) y políticas de tiempo de vida (TTL) diferenciadas según la volatilidad del recurso.
2. **Channel Layer para WebSockets:** Uso del backend `channels_redis.core.RedisChannelLayer` para orquestar grupos de chat en tiempo real.
3. **Almacenamiento de Rate Limiting y Métricas:** Registro de contadores atómicos y muestreos de latencia circular en memoria.

## Consecuencias
### Positivas
- Reducción drástica del tiempo de respuesta (latencias warm cache inferiores a $5\text{ ms}$).
- Comunicación entre procesos desacoplada para envío de eventos de chat y notificaciones.
- Operaciones atómicas (`incr`, `decr`) de alta concurrencia.

### Negativas / Retos
- Requiere una disciplina rigurosa de invalidación de caché para evitar servir datos obsoletos tras actualizaciones en el modelo.
