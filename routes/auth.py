from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from db.supabase_client import supabase
from decimal import Decimal

# Register, login, and refresh token routes 

router = APIRouter()


# Schema defs

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# helper methods from supabase

def create_user_record(user_id: str, email: str, username: str):
    """ Create a new user in 'users' table after auth signup """
    try:
        starting_balance = Decimal("1500.00")

        res = supabase.table("users").insert({
            "id": user_id,
            "email": email,
            "username": username,
            "balance": starting_balance
        }).execute()

        if res.error: 
            raise HTTPException(status_code=500, detail=f"Error creating user record: {res.error.message}")
        
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Exception creating user record: {str(e)}")
    
def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """ Set secure cookies for tokens. """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60*60  # 1 hour
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30*24*60*60  # 30 days
    )

# routes

@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, response: Response):
    """
    Register a new user: 
    1. Create Auth user in Supabase.
    2. Insert into users table with starting balance.
    3. Return and set auth tokens in cookies.
    """

    try:
        auth_res = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password
        })

        if not auth_res.user:
            raise HTTPException(status_code=400, detail="Failed to register user")
        
        user_id = auth_res.user.id
        create_user_record(user_id, req.email, req.username)

        session = auth_res.session
        if not session:
            raise HTTPException(status_code=500, detail="No session returned after registration")
        
        set_auth_cookies(response, session.access_token, session.refresh_token)

        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/login", response_model=TokenResponse)
def login_user(req: LoginRequest, response: Response):
    """
    Login an existing user:
    1. Authenticate via Supabase Auth.
    2. Return and set auth tokens in cookies.
    """

    try:
        auth_res = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })

        if not auth_res.user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        session = auth_res.session
        if not session:
            raise HTTPException(status_code=500, detail="No session returned after login")
        
        set_auth_cookies(response, session.access_token, session.refresh_token)

        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request, response: Response):
    """
    Refresh auth tokens using the refresh token cookie.
    """

    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token provided")
        
        refreshed = supabase.auth.refresh_session(refresh_token)
        if not refreshed.session:
            raise HTTPException(status_code=401, detail="Failed to refresh session")
        
        session = refreshed.session
        set_auth_cookies(response, session.access_token, session.refresh_token)

        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
