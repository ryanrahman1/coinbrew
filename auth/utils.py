import bcrypt

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a stored password against one provided by user."""
    return bcrypt.checkpw(password.encode(), hashed.encode())
