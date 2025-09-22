from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title="BookSocial API", version="0.1.0")

@app.get("/")
def root():
  return {"message": f"Bienvenido a {settings.PROJECT_NAME}"}

@app.get("/api/v1/health")
def health():
  return {"status": "ok"}
