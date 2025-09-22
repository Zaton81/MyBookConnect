# ─── Etapa Base ───
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Etapa de Producción ───
FROM base AS production
COPY . .
EXPOSE 8000
# Fíjate que hemos quitado --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ─── Etapa de Desarrollo ───
FROM base AS development
COPY . .
EXPOSE 8000
# El modo desarrollo mantiene el --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]