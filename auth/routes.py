from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from auth.utils import hash_password, verify_password
from db.queries import get_user_by_username, create_user, get_user_by_id

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(request: RegisterRequest):
    existing_user = get_user_by_username(request.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = hash_password(request.password)
    create_user(request.username, hashed)
    return {"message": "User registered successfully"}

@router.post("/login")
def login(request: LoginRequest):
    user = get_user_by_username(request.username)
    if not user or not verify_password(request.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {"message": "Login successful", "user_id": user["id"]}


@router.get("/user/{user_id}")
def get_user(user_id: int):
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user["id"],
        "username": user["username"],
        "balance": user["balance"]
    }
