import re
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import StoreWebhook, User, get_db
from ..dependencies import require_authenticated_user
from ..routers.stores import editable_store, owned_store
from ..schemas import WebhookIn, WebhookTestIn, WebhookUpdate
from ..services.webhooks import test_webhook_url

router = APIRouter(prefix="/api/stores/me/webhook", tags=["webhooks"])
DISCORD_WEBHOOK_PATH = re.compile(r"^/api/webhooks/\d+/[^/?#]+/?$")
DISCORD_HOSTS = {"discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"}


def validate_discord_webhook_url(value: str) -> str:
    url = value.strip()
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="URL must be a valid Discord webhook URL") from exc
    if parsed.scheme != "https" or parsed.hostname not in DISCORD_HOSTS or port not in {None, 443} or parsed.username or parsed.password or not DISCORD_WEBHOOK_PATH.fullmatch(parsed.path):
        raise HTTPException(status_code=422, detail="URL must be a valid Discord webhook URL")
    if parsed.query or parsed.fragment:
        raise HTTPException(status_code=422, detail="Discord webhook URL must not contain a query or fragment")
    return url


def webhook_dict(webhook: StoreWebhook) -> dict:
    return {
        "id": webhook.id,
        "store_id": webhook.store_id,
        "name": webhook.name,
        "url": webhook.url,
        "active": webhook.active,
        "created_at": webhook.created_at.isoformat(),
        "updated_at": webhook.updated_at.isoformat(),
    }


@router.get("")
def get_webhook(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    webhook = db.query(StoreWebhook).filter(StoreWebhook.store_id == store.id).one_or_none()
    return webhook_dict(webhook) if webhook else None


@router.post("")
def save_webhook(payload: WebhookIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    url = validate_discord_webhook_url(payload.url)
    webhook = db.query(StoreWebhook).filter(StoreWebhook.store_id == store.id).one_or_none()
    if webhook:
        webhook.name = payload.name.strip()
        webhook.url = url
        webhook.active = payload.active
    else:
        webhook = StoreWebhook(store_id=store.id, name=payload.name.strip(), url=url, active=payload.active)
        db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook_dict(webhook)


@router.patch("")
def update_webhook(payload: WebhookUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    webhook = db.query(StoreWebhook).filter(StoreWebhook.store_id == store.id).one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook is not configured")
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        webhook.name = changes["name"].strip()
    if "url" in changes:
        webhook.url = validate_discord_webhook_url(changes["url"])
    if "active" in changes:
        webhook.active = changes["active"]
    db.commit()
    db.refresh(webhook)
    return webhook_dict(webhook)


@router.delete("")
def delete_webhook(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    webhook = db.query(StoreWebhook).filter(StoreWebhook.store_id == store.id).one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook is not configured")
    db.delete(webhook)
    db.commit()
    return {"status": "deleted"}


@router.post("/test")
def test_webhook(payload: WebhookTestIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    url = validate_discord_webhook_url(payload.url)
    result = test_webhook_url(url, {
        "content": f"Test webhook from {store.name}",
        "username": "TokTok",
    })
    return {"url": url, **result}
