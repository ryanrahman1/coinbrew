from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client
import os
from config import supabase  

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str

class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(request: RegisterRequest):
    auth_res = supabase.auth.sign_up({
        "email": request.email,
        "password": request.password,
    })

    if not auth_res.user:
        raise HTTPException(status_code=400, detail="Registration failed")

    user_id = auth_res.user.id

    supabase.table("users").insert({
        "id": user_id, 
        "username": request.username,
        "email": request.email,
        "balance": 1500.0
    }).execute()

    return {"message": "User registered successfully", "user_id": user_id}


@router.post("/login")
def login(request: LoginRequest):
    auth_res = supabase.auth.sign_in_with_password({
        "email": request.email,
        "password": request.password,
    })

    if not auth_res.session:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response = JSONResponse({
        "message": "Login successful",
        "access_token": auth_res.session.access_token,
        "user_id": auth_res.user.id
    })

    response.set_cookie(
        key="refresh_token",
        value=auth_res.session.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.post("/refresh")
def refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    auth_res = supabase.auth.refresh_session(refresh_token)
    if not auth_res.session:
        raise HTTPException(status_code=401, detail="Failed to refresh session")

    response = JSONResponse({
        "access_token": auth_res.session.access_token,
        "user_id": auth_res.user.id
    })

    response.set_cookie(
        key="refresh_token",
        value=auth_res.session.refresh_token,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.post("/logout")
def logout():
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("refresh_token")
    return response
