from fastapi import Header, HTTPException
import os
from dotenv import load_dotenv

load_dotenv()


ADMIN_KEY = os.getenv("ADMIN_KEY")
def verify_admin_key(x_admin_key: str = Header(None)):
    """
    Dependency for admin routes.
    Checks X-Admin-Key header against environment key.
    """
    if not x_admin_key:
        raise HTTPException(status_code=401, detail="Missing admin key")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return True