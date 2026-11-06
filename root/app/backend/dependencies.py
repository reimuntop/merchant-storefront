from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import User, get_db


def require_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_authenticated_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_access_token(token)
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    store_id = payload.get("store_id")
    store_role = payload.get("store_role")
    if store_id is not None and not isinstance(store_id, int):
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    if store_role not in {None, "owner", "editor", "viewer"}:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    user = require_user(db, user_id)
    user._token_store_id = store_id
    user._token_store_role = store_role
    return user


def require_same_user(auth_user: User, requested_user_id: int) -> None:
    if auth_user.id != requested_user_id:
        raise HTTPException(status_code=403, detail="You can only access your own account")
