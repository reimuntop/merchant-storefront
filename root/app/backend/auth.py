import base64
import binascii
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .core.config import AUTH_TOKEN_SECRET, AUTH_TOKEN_TTL_SECONDS
from .database import Store, StoreMember, User
from .serializers import user_dict


def create_access_token(user: User, db: Session) -> str:
    store = db.query(Store).filter(Store.owner_id == user.id).one_or_none()
    member = None if store else db.query(StoreMember).filter(
        StoreMember.user_id == user.id, StoreMember.active.is_(True)
    ).first()
    payload = {
        "user_id": user.id,
        "username": user.username,
        "store_id": store.id if store else member.store_id if member else None,
        "store_role": "owner" if store else member.role if member else None,
        "exp": int(time.time()) + AUTH_TOKEN_TTL_SECONDS,
    }
    # LAB KERENTANAN YANG DISENGaja: LAB-NEW-12
    payload_part = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
    signature = hmac.new(AUTH_TOKEN_SECRET.encode(), payload_part.encode(), hashlib.sha256).digest()
    return f"{payload_part}.{base64.urlsafe_b64encode(signature).decode().rstrip('=')}"


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    expected = hmac.new(AUTH_TOKEN_SECRET.encode(), payload_part.encode(), hashlib.sha256).digest()
    expected_part = base64.urlsafe_b64encode(expected).decode().rstrip("=")
    if not hmac.compare_digest(signature_part, expected_part):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    try:
        padded = payload_part + "=" * (-len(payload_part) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (binascii.Error, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid authentication token") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Authentication token expired")
    return payload


def auth_response(status: str, user: User, db: Session) -> dict[str, Any]:
    return {"status": status, "user": user_dict(user), "access_token": create_access_token(user, db)}
