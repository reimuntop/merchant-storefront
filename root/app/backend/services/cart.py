from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database import CartCheckoutState, CartCouponState, CartItem, Product, ProductVariant


def cart_unit_price(item: CartItem) -> float:
    if item.unit_price_snapshot is not None:
        return item.unit_price_snapshot
    if item.variant and item.variant.price is not None:
        return item.variant.price
    return item.product.price


def clear_checkout_state_if_cart_empty(db: Session, user_id: int) -> None:
    db.flush()
    if not db.query(CartItem.id).filter(CartItem.user_id == user_id).first():
        checkout_state = db.get(CartCheckoutState, user_id)
        coupon_state = db.get(CartCouponState, user_id)
        if checkout_state:
            db.delete(checkout_state)
        if coupon_state:
            db.delete(coupon_state)


def add_to_cart(db: Session, user_id: int, product_id: int, quantity: int = 1, variant_id: int | None = None) -> dict[str, Any]:
    if quantity < 1:
        raise HTTPException(status_code=422, detail="Cart quantity must be at least 1")
    product = db.get(Product, product_id)
    if not product:
        return {"status": "error", "message": f"Product {product_id} not found"}
    variant = None
    if variant_id is not None:
        variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id, ProductVariant.active.is_(True)).one_or_none()
        if not variant:
            return {"status": "error", "message": "Product variant not found"}
    item = db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.product_id == product_id).one_or_none()
    if item and item.variant_id != variant_id:
        item = None
    if item:
        available_stock = variant.stock if variant else product.stock
        if available_stock is not None and item.quantity + quantity > available_stock:
            return {"status": "error", "message": "Requested quantity exceeds available stock"}
        if item.unit_price_snapshot is None:
            item.unit_price_snapshot = variant.price if variant and variant.price is not None else product.price
        item.quantity += quantity
    else:
        available_stock = variant.stock if variant else product.stock
        if available_stock is not None and quantity > available_stock:
            return {"status": "error", "message": "Requested quantity exceeds available stock"}
        unit_price_snapshot = variant.price if variant and variant.price is not None else product.price
        item = CartItem(user_id=user_id, product_id=product_id, variant_id=variant_id, quantity=quantity,
                        unit_price_snapshot=unit_price_snapshot)
        db.add(item)
    db.commit()
    return {"status": "added", "user_id": user_id, "product_id": product_id, "variant_id": variant_id, "quantity": item.quantity}


def remove_from_cart(db: Session, user_id: int, product_id: int, quantity: int = 1, variant_id: int | None = None) -> dict[str, Any]:
    item = db.query(CartItem).filter(CartItem.user_id == user_id, CartItem.product_id == product_id, CartItem.variant_id == variant_id).one_or_none()
    if not item:
        return {"status": "not_found", "user_id": user_id, "product_id": product_id}
    item.quantity -= quantity
    remaining = max(item.quantity, 0)
    if item.quantity <= 0:
        db.delete(item)
    clear_checkout_state_if_cart_empty(db, user_id)
    db.commit()
    return {"status": "removed", "user_id": user_id, "product_id": product_id, "quantity": remaining}
