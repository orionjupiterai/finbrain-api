from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Dict, List, Optional

app = FastAPI(
    title="FinBrain API",
    description="Personal Finance Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
users_db: Dict[str, dict] = {}
sessions: Dict[str, str] = {}

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    is_officer: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    email: str
    full_name: str
    is_officer: bool
    created_at: str

@app.get("/")
def root():
    return {
        "message": "Welcome to FinBrain API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "register": "POST /api/v1/auth/register",
            "login": "POST /api/v1/auth/login",
            "profile": "GET /api/v1/users/me"
        }
    }

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_db[user.email] = {
        "email": user.email,
        "password": user.password,  # In production, this would be hashed
        "full_name": user.full_name,
        "is_officer": user.is_officer,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return UserResponse(**users_db[user.email])

@app.post("/api/v1/auth/login")
async def login(user: UserLogin):
    if user.email not in users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if users_db[user.email]["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Simple token (in production, use JWT)
    token = f"token-{user.email}-{datetime.utcnow().timestamp()}"
    sessions[token] = user.email
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(**users_db[user.email])
    }

@app.get("/api/v1/users/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    if token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = sessions[token]
    return UserResponse(**users_db[email])

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/status")
def api_status():
    return {
        "api_version": "v1",
        "status": "active",
        "registered_users": len(users_db),
        "active_sessions": len(sessions)
    }
