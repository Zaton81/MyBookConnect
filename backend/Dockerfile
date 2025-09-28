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
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "mybookconnect.wsgi:application"]

# ─── Etapa de Desarrollo ───
FROM base AS development
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]