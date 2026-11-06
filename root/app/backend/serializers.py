from typing import Any, Optional

from .database import Address, Discount, Product, ProductClaim, ProductQuestion, ProductVariant, Purchase, Refund, ReturnRequest, Review, Store, StoreCategory, User


def user_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
    }


def product_dict(product: Product) -> dict[str, Any]:
    variants = list(getattr(product, "variants", []))
    effective_status = product.status
    if product.status == "active":
        if variants and not any(variant.active and variant.stock > 0 for variant in variants):
            effective_status = "out-of-stock"
        elif not variants and product.stock is not None and product.stock <= 0:
            effective_status = "out-of-stock"
    return {
        "id": product.id, "name": product.name, "description": product.description,
        "price": product.price, "image_url": product.image_url, "category": product.category,
        "store_id": product.store_id, "category_id": product.category_id, "stock": product.stock,
        "sku": product.sku, "status": effective_status,
        "store": store_dict(product.store) if product.store else None,
        "variants": [variant_dict(variant) for variant in variants],
    }


def review_dict(review: Review, author_name: Optional[str] = None) -> dict[str, Any]:
    anonymous = bool(review.is_anonymous)
    return {
        "id": review.id, "user_id": review.user_id, "product_id": review.product_id,
        "rating": review.rating, "body": review.body, "is_anonymous": anonymous,
        "author_name": "Anonymous User" if anonymous else author_name or f"User #{review.user_id}",
        "created_at": review.created_at.isoformat(),
    }


def question_dict(question: ProductQuestion) -> dict[str, Any]:
    return {
        "id": question.id, "product_id": question.product_id,
        "user_id": question.user_id, "message": question.message,
        "answer": question.answer, "created_at": question.created_at.isoformat(),
        "answered_at": question.answered_at.isoformat() if question.answered_at else None,
        "product_name": question.product.name,
        "customer_name": question.user.display_name,
    }


def claim_dict(claim: ProductClaim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "product_id": claim.product_id,
        "user_id": claim.user_id,
        "status": claim.status,
        "created_at": claim.created_at.isoformat(),
    }


def store_dict(store: Store) -> dict[str, Any]:
    return {
        "id": store.id, "owner_id": store.owner_id, "name": store.name, "slug": store.slug,
        "description": store.description, "category": store.category, "city": store.city,
        "phone": store.phone, "created_at": store.created_at.isoformat(),
        "logo_url": store.logo_url, "banner_url": store.banner_url, "address": store.address,
        "opening_hours": store.opening_hours, "return_policy": store.return_policy,
    }


def category_dict(category: StoreCategory) -> dict[str, Any]:
    return {
        "id": category.id,
        "store_id": category.store_id,
        "name": category.name,
        "slug": category.slug,
        "created_at": category.created_at.isoformat(),
    }


def discount_dict(discount: Discount) -> dict[str, Any]:
    return {
        "id": discount.id,
        "store_id": discount.store_id,
        "code": discount.code,
        "kind": discount.kind,
        "value": discount.value,
        "min_subtotal": discount.min_subtotal,
        "starts_at": discount.starts_at.isoformat() if discount.starts_at else None,
        "ends_at": discount.ends_at.isoformat() if discount.ends_at else None,
        "usage_limit": discount.usage_limit,
        "usage_count": discount.usage_count,
        "active": discount.active,
        "scope": discount.scope or "all",
        "target_id": discount.target_id,
        "created_at": discount.created_at.isoformat(),
    }


def variant_dict(variant: ProductVariant) -> dict[str, Any]:
    return {
        "id": variant.id, "product_id": variant.product_id, "name": variant.name,
        "size": variant.size, "color": variant.color, "sku": variant.sku,
        "stock": variant.stock, "price": variant.price, "active": variant.active,
        "created_at": variant.created_at.isoformat(),
    }


def address_dict(address: Address) -> dict[str, Any]:
    return {
        "id": address.id, "user_id": address.user_id, "label": address.label,
        "recipient_name": address.recipient_name, "phone": address.phone,
        "address_line": address.address_line, "city": address.city,
        "postal_code": address.postal_code, "is_default": address.is_default,
        "created_at": address.created_at.isoformat(),
    }


def purchase_dict(purchase: Purchase) -> dict[str, Any]:
    return {
        "id": purchase.id, "user_id": purchase.user_id, "product": product_dict(purchase.product),
        "quantity": purchase.quantity, "total": purchase.total,
        "purchased_at": purchase.purchased_at.isoformat(), "status": purchase.status,
        "discount_code": purchase.discount_code, "discount_amount": purchase.discount_amount,
        "shipping_fee": purchase.shipping_fee,
        "shipping_address_id": purchase.shipping_address_id,
        "variant_id": purchase.variant_id,
        "refund": refund_dict(purchase.refund) if purchase.refund else None,
        "return_request": return_request_dict(purchase.return_request) if purchase.return_request else None,
    }


def refund_dict(refund: Refund) -> dict[str, Any]:
    return {
        "id": refund.id,
        "purchase_id": refund.purchase_id,
        "user_id": refund.user_id,
        "refund_amount": refund.amount,
        "reason": refund.reason,
        "status": refund.status,
        "created_at": refund.created_at.isoformat(),
    }


def return_request_dict(return_request: ReturnRequest) -> dict[str, Any]:
    return {
        "id": return_request.id,
        "purchase_id": return_request.purchase_id,
        "user_id": return_request.user_id,
        "quantity": return_request.quantity,
        "reason": return_request.reason,
        "status": return_request.status,
        "refund_amount": return_request.refund_amount,
        "created_at": return_request.created_at.isoformat(),
    }
