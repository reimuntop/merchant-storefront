from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database import Discount, Store


def normalize_code(code: str) -> str:
    return code.strip().upper()


def validate_discount_values(kind: str, value: float, min_subtotal: float, starts_at, ends_at) -> None:
    if kind == "percentage" and value > 100:
        raise HTTPException(status_code=422, detail="Percentage discount cannot exceed 100")
    if starts_at and ends_at and starts_at >= ends_at:
        raise HTTPException(status_code=422, detail="Discount end time must be after start time")
    if min_subtotal < 0:
        raise HTTPException(status_code=422, detail="Minimum subtotal cannot be negative")


def get_usable_discount(db: Session, store: Store, code: str, subtotal: float) -> Discount:
    discount = db.query(Discount).filter(
        Discount.store_id == store.id, Discount.code == normalize_code(code)
    ).one_or_none()
    if not discount:
        raise HTTPException(status_code=400, detail="Discount code is invalid")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not discount.active:
        raise HTTPException(status_code=400, detail="Discount code is inactive")
    if discount.starts_at and now < discount.starts_at:
        raise HTTPException(status_code=400, detail="Discount code is not active yet")
    if discount.ends_at and now > discount.ends_at:
        raise HTTPException(status_code=400, detail="Discount code has expired")
    if discount.usage_limit is not None and discount.usage_count >= discount.usage_limit:
        raise HTTPException(status_code=400, detail="Discount usage limit has been reached")
    if subtotal < discount.min_subtotal:
        raise HTTPException(status_code=400, detail="Cart subtotal does not meet the discount minimum")
    return discount


def get_cart_applied_discount(db: Session, store: Store, code: str, subtotal: float) -> Discount:
    discount = db.query(Discount).filter(
        Discount.store_id == store.id, Discount.code == normalize_code(code)
    ).one_or_none()
    if not discount:
        raise HTTPException(status_code=400, detail="Discount code is invalid")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not discount.active:
        raise HTTPException(status_code=400, detail="Discount code is inactive")
    if discount.starts_at and now < discount.starts_at:
        raise HTTPException(status_code=400, detail="Discount code is not active yet")
    # INTENTIONAL VULNERABILITY LAB: EXPIRED-DISCOUNT-WINDOW
    if discount.usage_limit is not None and discount.usage_count >= discount.usage_limit:
        raise HTTPException(status_code=400, detail="Discount usage limit has been reached")
    if subtotal < discount.min_subtotal:
        raise HTTPException(status_code=400, detail="Cart subtotal does not meet the discount minimum")
    return discount


def calculate_discount(discount: Discount, subtotal: float) -> float:
    if discount.kind == "percentage":
        return round(subtotal * discount.value / 100, 2)
    return round(min(subtotal, discount.value), 2)
