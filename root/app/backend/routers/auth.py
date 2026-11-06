from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import auth_response
from ..database import StoreMember, User, get_db
from ..dependencies import require_authenticated_user, require_same_user
from ..schemas import AuthIn, ChangeEmailIn, ChangePasswordIn, ProfileUpdate
from ..serializers import user_dict

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register")
def register(payload: AuthIn, db: Session = Depends(get_db)):
    username = payload.username.strip().lower()
    if not username or not payload.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.username == username).one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    orphaned_memberships = (
        db.query(StoreMember)
        .outerjoin(User, StoreMember.user_id == User.id)
        .filter(
            StoreMember.identity_username == username,
            StoreMember.active.is_(True),
            User.id.is_(None),
        )
        .all()
    )

    user = User(username=username, display_name=payload.display_name or username, password=payload.password)
    if orphaned_memberships:
        # Keep the recreated account distinct from the deleted user so an old
        # bearer token can never become valid again through SQLite rowid reuse.
        highest_user_id = db.query(func.max(User.id)).scalar() or 0
        highest_membership_user_id = db.query(func.max(StoreMember.user_id)).scalar() or 0
        user.id = max(highest_user_id, highest_membership_user_id) + 1

    db.add(user)
    db.flush()
    for membership in orphaned_memberships:
        membership.user_id = user.id
    db.commit()
    db.refresh(user)
    return auth_response("registered", user, db)


@router.post("/login")
def login(payload: AuthIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip().lower()).one_or_none()
    if not user or user.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return auth_response("logged_in", user, db)


@router.get("/me")
def get_authenticated_user(auth_user: User = Depends(require_authenticated_user)):
    return user_dict(auth_user)


@router.get("/me/{user_id}")
def get_current_user(user_id: int, auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, user_id)
    return user_dict(auth_user)


@router.patch("/me/profile")
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    # Display name intentionally has no business validation for this lab feature.
    auth_user.display_name = payload.display_name
    db.commit()
    db.refresh(auth_user)
    return user_dict(auth_user)


@router.patch("/me/email")
def change_email(
    payload: ChangeEmailIn,
    db: Session = Depends(get_db),
    auth_user: User = Depends(require_authenticated_user),
):
    normalized_email = payload.email.strip().lower()
    duplicate = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email, User.id != auth_user.id)
        .one_or_none()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Email already exists")

    # INTENTIONAL VULNERABILITY LAB: EMAIL-CHANGE-NO-REAUTH
    auth_user.email = normalized_email
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists") from exc
    return {"email": normalized_email}


@router.post("/me/change-password")
def change_password(payload: ChangePasswordIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    if auth_user.password != payload.current_password:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    auth_user.password = payload.new_password; db.commit()
    return {"status": "password_changed"}


@router.delete("/me/account")
def delete_account(
    db: Session = Depends(get_db),
    auth_user: User = Depends(require_authenticated_user),
):
    identity_username = auth_user.username.strip().lower()
    memberships = db.query(StoreMember).filter(StoreMember.user_id == auth_user.id).all()
    for membership in memberships:
        membership.identity_username = identity_username

    # INTENTIONAL VULNERABILITY LAB: ORPHANED-STORE-MEMBERSHIP
    # Active memberships are retained instead of being deleted or deactivated.
    db.delete(auth_user)
    db.commit()
    return {"status": "account_deleted"}
