from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from .core.config import Settings
from .models import User
from .database import get_db, init_db

app = FastAPI()
settings = Settings()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth schemas
class UserBase(BaseModel):
    username: str
    email: str
    birth_date: Optional[datetime] = None
    location: Optional[str] = None
    privacy_level: str = "public"

class UserCreate(UserBase):
    password: str
    password2: str

class UserUpdate(BaseModel):
    birth_date: Optional[datetime] = None
    location: Optional[str] = None
    privacy_level: Optional[str] = None
    avatar: Optional[str] = None

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Endpoints
@app.post("/users/", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if user.password != user.password2:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    db_user = await User.get_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return await User.create(db=db, user=user)

@app.patch("/users/me", response_model=User)
async def update_user(
    avatar: Optional[UploadFile] = File(None),
    user_update: UserUpdate = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    update_data = user_update.dict(exclude_unset=True)
    
    if avatar:
        filename = f"avatars/{current_user.id}_{avatar.filename}"
        contents = await avatar.read()
        # Save the file
        with open(f"static/{filename}", "wb") as f:
            f.write(contents)
        update_data["avatar"] = filename
    
    updated_user = await current_user.update(db, **update_data)
    return updated_user

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()