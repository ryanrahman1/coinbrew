
from fastapi import Header, HTTPException
from db.supabase_client import supabase
from typing import Any


class UserProxy(dict):
    """A lightweight proxy that allows both attribute and dict-style access.

    Example: user.id and user['id'] will both work.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def _normalize_user_obj(user_obj: Any) -> UserProxy:
    # If supabase returns a plain dict, use it directly.
    if isinstance(user_obj, dict):
        return UserProxy(user_obj)

    # If it's an object with attributes, extract public attrs.
    data = {}
    try:
        for attr in dir(user_obj):
            if attr.startswith("_"):
                continue
            value = getattr(user_obj, attr)
            if callable(value):
                continue
            data[attr] = value
    except Exception:
        # Fallback to common fields
        data = {
            "id": getattr(user_obj, "id", None),
            "email": getattr(user_obj, "email", None),
            "username": getattr(user_obj, "username", None),
        }

    return UserProxy(data)


def get_current_user(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ", 1)[1]

    # supabase.auth.get_user may return an object with `.user` or a dict; handle both.
    res = supabase.auth.get_user(token)
    user_obj = None
    if hasattr(res, "user"):
        user_obj = res.user
    elif isinstance(res, dict):
        user_obj = res.get("user")

    if not user_obj:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return _normalize_user_obj(user_obj)
