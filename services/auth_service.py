from __future__ import annotations

from functools import lru_cache
from flask import request

from config import config

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except Exception:  # pragma: no cover
    firebase_admin = None
    auth = None
    credentials = None


@lru_cache(maxsize=1)
def _firebase_ready() -> bool:
    if config.AUTH_MODE != "firebase" or not config.FIREBASE_SERVICE_ACCOUNT_PATH:
        return False
    if firebase_admin is None:
        return False
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_PATH)
            firebase_admin.initialize_app(cred)
        return True
    except Exception:
        return False


def verify_firebase_token(id_token: str) -> dict | None:
    if not _firebase_ready() or auth is None:
        return None
    try:
        return auth.verify_id_token(id_token)
    except Exception:
        return None


def get_user_id_from_request(req: request = request) -> str:
    """Demo mode accepts X-User-Id. Firebase mode verifies Authorization: Bearer <idToken>."""
    header_user = req.headers.get("X-User-Id") or req.args.get("user_id")
    if header_user:
        return header_user[:128]

    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        decoded = verify_firebase_token(auth_header.replace("Bearer ", "", 1).strip())
        if decoded and decoded.get("uid"):
            return decoded["uid"]

    return "demo_user"
