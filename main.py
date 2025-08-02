from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import uuid

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

# In-memory storage
users_db: Dict[str, dict] = {}
sessions: Dict[str, str] = {}
accounts_db: Dict[str, dict] = {}

# Enums
class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    loan = "loan"
    investment = "investment"

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

class AccountCreate(BaseModel):
    account_type: AccountType
    account_name: str
    institution: str
    balance: float = 0.0
    credit_limit: Optional[float] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None

class AccountResponse(BaseModel):
    id: str
    user_email: str
    account_type: AccountType
    account_name: str
    institution: str
    balance: float
    credit_limit: Optional[float] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    created_at: str
    updated_at: str

class AccountUpdate(BaseModel):
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None

class AccountsSummary(BaseModel):
    total_assets: float
    total_liabilities: float
    net_worth: float
    accounts_by_type: Dict[str, List[AccountResponse]]
    total_by_type: Dict[str, float]

# Helper function to get current user
async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    if token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return sessions[token]

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Welcome to FinBrain API",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "auth": {
                "register": "POST /api/v1/auth/register",
                "login": "POST /api/v1/auth/login"
            },
            "users": {
                "me": "GET /api/v1/users/me"
            },
            "accounts": {
                "create": "POST /api/v1/accounts",
                "list": "GET /api/v1/accounts",
                "get": "GET /api/v1/accounts/{account_id}",
                "update": "PUT /api/v1/accounts/{account_id}",
                "delete": "DELETE /api/v1/accounts/{account_id}",
                "summary": "GET /api/v1/accounts/summary"
            }
        }
    }

# Auth endpoints
@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_db[user.email] = {
        "email": user.email,
        "password": user.password,
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
    
    token = f"token-{user.email}-{datetime.utcnow().timestamp()}"
    sessions[token] = user.email
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(**users_db[user.email])
    }

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: str = Depends(get_current_user)):
    return UserResponse(**users_db[current_user])

# Financial Accounts endpoints
@app.post("/api/v1/accounts", response_model=AccountResponse)
async def create_account(
    account: AccountCreate,
    current_user: str = Depends(get_current_user)
):
    """Create a new financial account"""
    account_id = str(uuid.uuid4())
    
    account_data = {
        "id": account_id,
        "user_email": current_user,
        "account_type": account.account_type,
        "account_name": account.account_name,
        "institution": account.institution,
        "balance": account.balance,
        "credit_limit": account.credit_limit,
        "interest_rate": account.interest_rate,
        "minimum_payment": account.minimum_payment,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    accounts_db[account_id] = account_data
    return AccountResponse(**account_data)

@app.get("/api/v1/accounts", response_model=List[AccountResponse])
async def list_accounts(current_user: str = Depends(get_current_user)):
    """List all accounts for the current user"""
    user_accounts = [
        AccountResponse(**account) 
        for account in accounts_db.values() 
        if account["user_email"] == current_user
    ]
    return user_accounts

@app.get("/api/v1/accounts/summary", response_model=AccountsSummary)
async def get_accounts_summary(current_user: str = Depends(get_current_user)):
    """Get financial summary of all accounts"""
    user_accounts = [
        account for account in accounts_db.values() 
        if account["user_email"] == current_user
    ]
    
    total_assets = 0
    total_liabilities = 0
    accounts_by_type = {}
    total_by_type = {}
    
    for account in user_accounts:
        account_type = account["account_type"]
        
        # Initialize type if not exists
        if account_type not in accounts_by_type:
            accounts_by_type[account_type] = []
            total_by_type[account_type] = 0
        
        accounts_by_type[account_type].append(AccountResponse(**account))
        
        # Calculate totals
        if account_type in ["checking", "savings", "investment"]:
            total_assets += account["balance"]
            total_by_type[account_type] += account["balance"]
        elif account_type in ["credit_card", "loan"]:
            total_liabilities += abs(account["balance"])
            total_by_type[account_type] += abs(account["balance"])
    
    return AccountsSummary(
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=total_assets - total_liabilities,
        accounts_by_type=accounts_by_type,
        total_by_type=total_by_type
    )

@app.get("/api/v1/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get specific account details"""
    if account_id not in accounts_db:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts_db[account_id]
    if account["user_email"] != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this account")
    
    return AccountResponse(**account)

@app.put("/api/v1/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    update_data: AccountUpdate,
    current_user: str = Depends(get_current_user)
):
    """Update account details"""
    if account_id not in accounts_db:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts_db[account_id]
    if account["user_email"] != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to update this account")
    
    # Update fields if provided
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        account[field] = value
    
    account["updated_at"] = datetime.utcnow().isoformat()
    
    return AccountResponse(**account)

@app.delete("/api/v1/accounts/{account_id}")
async def delete_account(
    account_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete an account"""
    if account_id not in accounts_db:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = accounts_db[account_id]
    if account["user_email"] != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to delete this account")
    
    del accounts_db[account_id]
    return {"message": "Account deleted successfully"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/v1/status")
def api_status():
    return {
        "api_version": "v1",
        "status": "active",
        "registered_users": len(users_db),
        "active_sessions": len(sessions),
        "total_accounts": len(accounts_db)
    }
