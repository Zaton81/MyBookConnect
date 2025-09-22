from pydantic import BaseModel
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "BookSocial"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_key")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/booksocial")

settings = Settings()
