# ─── Etapa Base ───
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario sin privilegios para ejecución segura
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Etapa de Desarrollo ───
FROM base AS development
COPY . .
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "mybookconnect.asgi:application"]

# ─── Etapa de Producción ───
FROM base AS production
COPY --chown=appuser:appgroup . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/schema/ || exit 1
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "mybookconnect.asgi:application"]