"""Helpers para autenticação com Supabase."""

from typing import Any, Dict, Optional

from supabase_client import supabase


def _user_to_dict(user: Any) -> Optional[Dict[str, Any]]:
    if user is None:
        return None
    if isinstance(user, dict):
        return user
    if hasattr(user, "model_dump"):
        return user.model_dump()
    if hasattr(user, "__dict__"):
        return user.__dict__
    return None


def sign_up(email: str, password: str) -> Optional[Dict[str, Any]]:
    response = supabase.auth.sign_up({"email": email, "password": password})
    return _user_to_dict(getattr(response, "user", None))


def sign_in(email: str, password: str):
    response = supabase.auth.sign_in_with_password({"email": email, "password": password})
    user = _user_to_dict(getattr(response, "user", None))
    session = getattr(response, "session", None)
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def sign_out():
    return supabase.auth.sign_out()


def get_current_user(access_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not access_token:
        response = supabase.auth.get_user()
    else:
        response = supabase.auth.get_user(access_token)
    user = getattr(response, "user", None)
    return _user_to_dict(user)


def set_session(access_token: Optional[str], refresh_token: Optional[str]):
    if not access_token or not refresh_token:
        return
    supabase.auth.set_session(access_token, refresh_token)
