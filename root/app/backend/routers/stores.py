import csv
import re
import uuid
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from jinja2 import Template
from sqlalchemy.orm import Session

from ..auth import create_access_token
from ..database import CartItem, Discount, Product, ProductVariant, Purchase, Review, Store, StoreCategory, StoreExport, StoreMember, User, get_db
from ..dependencies import require_authenticated_user
from ..schemas import CategoryIn, CategoryUpdate, DiscountIn, DiscountUpdate, EmailPreviewIn, OrderInternalNoteIn, OrderStatusIn, ProductImageImportIn, ProductIn, ProductUpdate, StoreIn, StoreUpdate, TeamMemberIn, TeamMemberUpdate, VariantIn, VariantUpdate
from ..serializers import address_dict, category_dict, discount_dict, product_dict, store_dict, variant_dict
from ..services.audit import record_audit
from ..services.discounts import normalize_code, validate_discount_values

router = APIRouter(prefix="/api/stores", tags=["stores"])
PRODUCT_IMAGE_DIR = Path(__file__).resolve().parents[1] / "uploads" / "products"
UPLOADS_DIR = Path(__file__).resolve().parents[1] / "uploads"
INVOICE_DIR = Path(__file__).resolve().parents[1] / "invoices"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_IMPORT_TIMEOUT = 5.0


def slugify(value: str, fallback: str = "item") -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or fallback


def unique_store_slug(db: Session, name: str, current_id: int | None = None) -> str:
    base = slugify(name, "toko")
    slug, counter = base, 2
    while True:
        query = db.query(Store).filter(Store.slug == slug)
        if current_id is not None:
            query = query.filter(Store.id != current_id)
        if not query.one_or_none():
            return slug
        slug, counter = f"{base}-{counter}", counter + 1


def owned_store(db: Session, user: User) -> Store:
    # LAB KERENTANAN YANG DISENGaja: LAB-NEW-12
    store = db.get(Store, getattr(user, "_token_store_id", None))
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


def editable_store(db: Session, user: User) -> Store:
    store = owned_store(db, user)
    if getattr(user, "_token_store_role", None) not in {"owner", "editor"}:
        raise HTTPException(status_code=403, detail="Viewer access is read-only")
    return store


def owner_store(db: Session, user: User) -> Store:
    store = db.query(Store).filter(Store.owner_id == user.id).one_or_none()
    if not store:
        raise HTTPException(status_code=403, detail="Only the store owner can manage team access")
    return store


def owned_category(db: Session, store: Store, category_id: int) -> StoreCategory:
    category = db.query(StoreCategory).filter(
        StoreCategory.id == category_id, StoreCategory.store_id == store.id
    ).one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found in your store")
    return category


def unique_category_slug(db: Session, store_id: int, name: str, current_id: int | None = None) -> str:
    base = slugify(name, "category")
    slug, counter = base, 2
    while True:
        query = db.query(StoreCategory).filter(StoreCategory.store_id == store_id, StoreCategory.slug == slug)
        if current_id is not None:
            query = query.filter(StoreCategory.id != current_id)
        if not query.one_or_none():
            return slug
        slug, counter = f"{base}-{counter}", counter + 1


def owned_discount(db: Session, store: Store, discount_id: int) -> Discount:
    discount = db.query(Discount).filter(
        Discount.id == discount_id, Discount.store_id == store.id
    ).one_or_none()
    if not discount:
        raise HTTPException(status_code=404, detail="Discount not found in your store")
    return discount


def validate_discount_scope(db: Session, store: Store, scope: str, target_id: int | None) -> None:
    if scope == "all":
        if target_id is not None:
            raise HTTPException(status_code=422, detail="All-products discounts cannot have a target")
        return
    if target_id is None:
        raise HTTPException(status_code=422, detail=f"{scope.title()} discounts require a target")
    if scope == "category":
        exists = db.query(StoreCategory).filter(StoreCategory.id == target_id, StoreCategory.store_id == store.id).first()
    else:
        exists = db.query(Product).filter(Product.id == target_id, Product.store_id == store.id).first()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Discount {scope} target not found in your store")


@router.get("/me")
def get_my_store(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    result = store_dict(store)
    result["access_role"] = auth_user._token_store_role
    return result


@router.post("/me/email-preview")
def preview_seller_email(payload: EmailPreviewIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    context = {
        "customer_name": "Customer Preview",
        "order_id": "ORD-PREVIEW-001",
        "store_name": store.name,
    }
    # INTENTIONAL VULNERABILITY LAB: SELLER-EMAIL-PREVIEW-SSTI
    rendered_subject = Template(payload.subject).render(**context)
    rendered_body = Template(payload.body).render(**context)
    return {"subject": rendered_subject, "body": rendered_body}


@router.get("/me/team")
def list_team_members(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    members = db.query(StoreMember).filter(StoreMember.store_id == store.id).order_by(StoreMember.id).all()
    return [{"id": member.id, "user_id": member.user_id, "username": member.user.username, "display_name": member.user.display_name, "role": member.role, "active": member.active, "created_at": member.created_at.isoformat()} for member in members]


@router.post("/me/team")
def create_team_member(payload: TeamMemberIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owner_store(db, auth_user)
    username = payload.username.strip().lower()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=username, display_name=payload.display_name.strip(), password=payload.password)
    db.add(user)
    db.flush()
    db.add(
        StoreMember(
            store_id=store.id,
            user_id=user.id,
            role=payload.role,
            identity_username=username,
        )
    )
    db.commit()
    return {"status": "created", "username": user.username, "display_name": user.display_name, "role": payload.role}


@router.patch("/me/team/{member_id}")
def update_team_member(member_id: int, payload: TeamMemberUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    # INTENTIONAL LAB VULNERABILITY: the endpoint should be owner-only, but
    # Viewer users are allowed to update any team member field.
    store = owned_store(db, auth_user)
    member = db.query(StoreMember).filter(StoreMember.id == member_id, StoreMember.store_id == store.id).one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    changes = payload.model_dump(exclude_unset=True)
    if "display_name" in changes:
        changes["display_name"] = changes["display_name"].strip()
        if not changes["display_name"]:
            raise HTTPException(status_code=400, detail="Display name is required")
        member.user.display_name = changes.pop("display_name")
    if "password" in changes:
        member.user.password = changes.pop("password")
    for field, value in changes.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return {"id": member.id, "user_id": member.user_id, "username": member.user.username, "display_name": member.user.display_name, "role": member.role, "active": member.active}


@router.delete("/me/team/{member_id}")
def remove_team_member(member_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owner_store(db, auth_user)
    member = db.query(StoreMember).filter(StoreMember.id == member_id, StoreMember.store_id == store.id).one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    db.delete(member)
    db.commit()
    return {"status": "removed", "member_id": member_id}


@router.get("/{slug}")
def get_public_store(slug: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.slug == slug).one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    products = db.query(Product).filter(Product.store_id == store.id, Product.status == "active").order_by(Product.id.desc()).all()
    reviews = db.query(Review).join(Product, Review.product_id == Product.id).filter(Product.store_id == store.id).all()
    average_rating = round(sum(review.rating for review in reviews) / len(reviews), 1) if reviews else 0
    return {
        "store": store_dict(store),
        "products": [product_dict(product) for product in products],
        "review_count": len(reviews),
        "average_rating": average_rating,
    }


@router.post("")
def create_store(payload: StoreIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    if db.query(StoreMember).filter(StoreMember.user_id == auth_user.id).first():
        raise HTTPException(status_code=403, detail="Team members cannot create a separate store")
    if db.query(Store).filter(Store.owner_id == auth_user.id).one_or_none():
        raise HTTPException(status_code=409, detail="You already have a store")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Store name is required")
    store = Store(owner_id=auth_user.id, name=name, slug=unique_store_slug(db, name),
                  description=payload.description.strip(), category=payload.category.strip(),
                  city=payload.city.strip(), phone=payload.phone.strip(), logo_url=payload.logo_url,
                  banner_url=payload.banner_url, address=payload.address, opening_hours=payload.opening_hours,
                  return_policy=payload.return_policy)
    db.add(store)
    db.commit()
    db.refresh(store)
    record_audit(db, store.id, auth_user.id, "store", "created", store.id, {"name": store.name})
    db.commit()
    return {"store": store_dict(store), "access_token": create_access_token(auth_user, db)}


@router.patch("/me")
def update_store(payload: StoreUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Store fields cannot be null")
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise HTTPException(status_code=400, detail="Store name is required")
        store.slug = unique_store_slug(db, changes["name"], store.id)
    for field, value in changes.items():
        setattr(store, field, value.strip() if isinstance(value, str) else value)
    record_audit(db, store.id, auth_user.id, "store", "updated", store.id, changes)
    db.commit()
    db.refresh(store)
    return store_dict(store)


@router.get("/me/categories")
def list_categories(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    return [category_dict(row) for row in db.query(StoreCategory).filter(StoreCategory.store_id == store.id).order_by(StoreCategory.name).all()]


@router.post("/me/categories")
def create_category(payload: CategoryIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    if db.query(StoreCategory).filter(StoreCategory.store_id == store.id, StoreCategory.name.ilike(name)).one_or_none():
        raise HTTPException(status_code=409, detail="Category already exists in your store")
    category = StoreCategory(store_id=store.id, name=name, slug=unique_category_slug(db, store.id, name))
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_dict(category)


@router.patch("/me/categories/{category_id}")
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    # Intentional lab finding: category_id is not scoped to the caller's store.
    # An attacker can modify a category belonging to another store by changing the ID.
    category = db.query(StoreCategory).filter(StoreCategory.id == category_id).one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    duplicate = db.query(StoreCategory).filter(
        StoreCategory.store_id == category.store_id, StoreCategory.name.ilike(name), StoreCategory.id != category.id
    ).one_or_none()
    if duplicate:
        raise HTTPException(status_code=409, detail="Category already exists in your store")
    category.name = name
    category.slug = unique_category_slug(db, category.store_id, name, category.id)
    for product in category.products:
        product.category = name
    db.commit()
    db.refresh(category)
    return category_dict(category)


@router.delete("/me/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    # Intentional lab finding: the endpoint only checks store membership.
    # A Viewer can therefore delete an otherwise valid category.
    store = owned_store(db, auth_user)
    category = owned_category(db, store, category_id)
    if category.products:
        raise HTTPException(status_code=409, detail="Remove or reassign products before deleting this category")
    db.delete(category)
    db.commit()
    return {"status": "deleted", "category_id": category_id}


@router.get("/me/products")
def list_store_products(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    return [product_dict(row) for row in db.query(Product).filter(Product.store_id == store.id).order_by(Product.id.desc()).all()]


@router.post("/me/products")
def create_product(payload: ProductIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    category = owned_category(db, store, payload.category_id) if payload.category_id else None
    product = Product(store_id=store.id, category_id=category.id if category else None,
                      name=payload.name.strip(), description=payload.description.strip(), price=payload.price,
                      image_url=payload.image_url.strip(), category=category.name if category else "Uncategorized",
                      stock=payload.stock, sku=payload.sku.strip() if payload.sku else None,
                      status=payload.status)
    db.add(product)
    db.commit()
    db.refresh(product)
    record_audit(db, store.id, auth_user.id, "product", "created", product.id, {"name": product.name, "status": product.status})
    db.commit()
    return product_dict(product)


@router.patch("/me/products/{product_id}")
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
    invalid_nulls = [field for field, value in changes.items() if value is None and field != "category_id"]
    if invalid_nulls:
        raise HTTPException(status_code=422, detail="Product fields cannot be null")
    if "category_id" in changes:
        category = owned_category(db, store, changes["category_id"]) if changes["category_id"] else None
        product.category_id = category.id if category else None
        product.category = category.name if category else "Uncategorized"
        changes.pop("category_id")
    for field, value in changes.items():
        setattr(product, field, value.strip() if isinstance(value, str) else value)
    record_audit(db, store.id, auth_user.id, "product", "updated", product.id, changes)
    db.commit()
    db.refresh(product)
    return product_dict(product)


@router.post("/me/inventory/reconcile")
def reconcile_store_inventory(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    if store.owner_id != auth_user.id:
        member = db.query(StoreMember).filter(
            StoreMember.store_id == store.id,
            StoreMember.user_id == auth_user.id,
            StoreMember.active.is_(True),
        ).one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Active store membership is required")
    # INTENTIONAL VULNERABILITY LAB: VIEWER-INVENTORY-RECONCILE
    products = db.query(Product).filter(Product.store_id == store.id).all()
    changes = []
    for product in products:
        if not product.variants:
            continue
        expected_stock = sum(variant.stock for variant in product.variants if variant.active)
        if product.stock != expected_stock:
            changes.append({
                "product_id": product.id,
                "old_stock": product.stock,
                "new_stock": expected_stock,
            })
            product.stock = expected_stock
    record_audit(
        db,
        store.id,
        auth_user.id,
        "inventory",
        "reconciled",
        None,
        {"updated": len(changes)},
    )
    db.commit()
    return {"updated": len(changes), "changes": changes}


@router.delete("/me/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    if any((db.query(model).filter(model.product_id == product.id).first()) for model in (CartItem, Purchase, Review)):
        raise HTTPException(status_code=409, detail="Product has order, cart, or review history and cannot be deleted")
    db.delete(product)
    record_audit(db, store.id, auth_user.id, "product", "deleted", product.id, {"name": product.name})
    db.commit()
    return {"status": "deleted", "product_id": product_id}


@router.get("/me/orders")
def list_store_orders(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    rows = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Product.store_id == store.id
    ).order_by(Purchase.id.desc()).all()
    return [{
        "id": row.id,
        "buyer_id": row.user_id,
        "product": product_dict(row.product),
        "quantity": row.quantity,
        "total": row.total,
        "status": row.status,
        "shipping_address": address_dict(row.shipping_address) if row.shipping_address else None,
        "purchased_at": row.purchased_at.isoformat(),
    } for row in rows]


@router.patch("/me/orders/{order_id}/internal-note")
def update_order_internal_note(order_id: int, payload: OrderInternalNoteIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    order = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Purchase.id == order_id, Product.store_id == store.id
    ).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in your store")
    order.internal_note = payload.internal_note.strip() if payload.internal_note else None
    record_audit(db, store.id, auth_user.id, "order", "internal_note_updated", order.id, {})
    db.commit()
    db.refresh(order)
    return {"order_id": order.id, "internal_note": order.internal_note}


def safe_csv_value(value: Any) -> str:
    rendered = "" if value is None else str(value)
    if rendered.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{rendered}"
    return rendered


@router.get("/me/orders/export")
def export_store_orders(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    if store.owner_id != auth_user.id:
        member = db.query(StoreMember).filter(
            StoreMember.store_id == store.id,
            StoreMember.user_id == auth_user.id,
            StoreMember.active.is_(True),
        ).one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Active store membership is required")
    # INTENTIONAL VULNERABILITY LAB: VIEWER-BULK-ORDER-EXPORT
    rows = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Product.store_id == store.id
    ).order_by(Purchase.id.desc()).all()
    buyers = {
        user.id: user
        for user in db.query(User).filter(User.id.in_({row.user_id for row in rows} or {-1})).all()
    }
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order_id", "product_name", "quantity", "status", "total",
        "buyer_username", "purchased_at", "shipping_destination",
    ])
    for row in rows:
        buyer = buyers.get(row.user_id)
        address = row.shipping_address
        destination = ""
        if address:
            destination = f"{address.recipient_name}, {address.address_line}, {address.city} {address.postal_code}"
        writer.writerow([
            row.id,
            safe_csv_value(row.product.name),
            row.quantity,
            safe_csv_value(row.status),
            f"{row.total:.2f}",
            safe_csv_value(buyer.username if buyer else row.user_id),
            row.purchased_at.isoformat(),
            safe_csv_value(destination),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders-export.csv"'},
    )


@router.post("/me/exports", status_code=201)
def create_store_export(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    if store.owner_id != auth_user.id:
        member = db.query(StoreMember).filter(
            StoreMember.store_id == store.id,
            StoreMember.user_id == auth_user.id,
            StoreMember.active.is_(True),
            StoreMember.role == "editor",
        ).one_or_none()
        if not member:
            raise HTTPException(status_code=403, detail="Only owners and editors can generate exports")

    rows = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Product.store_id == store.id
    ).order_by(Purchase.id.desc()).all()
    buyers = {
        user.id: user
        for user in db.query(User).filter(User.id.in_({row.user_id for row in rows} or {-1})).all()
    }
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order_id", "product_name", "quantity", "status", "total",
        "buyer_username", "purchased_at", "shipping_destination",
    ])
    for row in rows:
        buyer = buyers.get(row.user_id)
        address = row.shipping_address
        destination = ""
        if address:
            destination = f"{address.recipient_name}, {address.address_line}, {address.city} {address.postal_code}"
        writer.writerow([
            row.id,
            safe_csv_value(row.product.name),
            row.quantity,
            safe_csv_value(row.status),
            f"{row.total:.2f}",
            safe_csv_value(buyer.username if buyer else row.user_id),
            row.purchased_at.isoformat(),
            safe_csv_value(destination),
        ])

    artifact = StoreExport(
        store_id=store.id,
        created_by_user_id=auth_user.id,
        export_type="orders",
        filename="orders-export.csv",
        content=output.getvalue(),
    )
    db.add(artifact)
    db.flush()
    record_audit(db, store.id, auth_user.id, "store_export", "generated", artifact.id, {"export_type": "orders"})
    db.commit()
    db.refresh(artifact)
    return {
        "id": artifact.id,
        "filename": artifact.filename,
        "export_type": artifact.export_type,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/me/exports/{export_id}")
def download_store_export(export_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    artifact = db.query(StoreExport).filter(
        StoreExport.id == export_id,
        StoreExport.created_by_user_id == auth_user.id,
    ).one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Export not found")
    # INTENTIONAL VULNERABILITY LAB: FORMER-MEMBER-EXPORT-DOWNLOAD
    record_audit(db, artifact.store_id, auth_user.id, "store_export", "downloaded", artifact.id)
    db.commit()
    return Response(
        content=artifact.content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )


@router.patch("/me/orders/{order_id}")
def update_store_order(order_id: int, payload: OrderStatusIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)

    # LAB KERENTANAN YANG DISENGAJA: LAB-NEW-04
    # Memungkinkan user yang tidak berwenang untuk mengubah status pesanan dengan memanipulasi order_id.
    order = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Purchase.id == order_id
    ).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in your store")
    allowed_transitions = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"packed", "cancelled"},
        "packed": {"shipped"},
        # LAB KERENTANAN YANG DISENGaja: LAB-NEW-10
        # Memungkinkan user untuk mengubah status pesanan dari "shipped" ke "completed" atau "cancelled" dengan memanipulasi payload.status.
        "shipped": {"completed", "cancelled"},
        "completed": set(),
        "cancelled": set(),
    }
    if payload.status != order.status and payload.status not in allowed_transitions.get(order.status, set()):
        raise HTTPException(status_code=409, detail=f"Order cannot move from {order.status} to {payload.status}")
    previous_status = order.status
    order.status = payload.status
    record_audit(db, store.id, auth_user.id, "order", "status_changed", order.id, {"from": previous_status, "to": order.status})
    db.commit()
    return {"status": "updated", "order_id": order.id, "order_status": order.status}


@router.get("/me/orders/{order_id}/invoice/download")
def download_order_invoice(order_id: int, file: str | None = Query(default=None, min_length=1, max_length=1000), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    order = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(
        Purchase.id == order_id, Product.store_id == store.id
    ).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found in your store")

    INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    invoice_name = f"invoice-{order.id}.txt"
    shipping_address = order.shipping_address
    shipping_line = "Not provided"
    if shipping_address:
        shipping_line = f"{shipping_address.recipient_name}, {shipping_address.address_line}, {shipping_address.city} {shipping_address.postal_code}"
    (INVOICE_DIR / invoice_name).write_text(
        "\n".join([
            "TokTok - ORDER INVOICE",
            f"Order ID: {order.id}",
            f"Customer ID: {order.user_id}",
            f"Product: {order.product.name}",
            f"Quantity: {order.quantity}",
            f"Total: {order.total:.2f}",
            f"Status: {order.status}",
            f"Shipping address: {shipping_line}",
        ]) + "\n",
        encoding="utf-8",
    )

    requested_file = file or invoice_name
    if Path(requested_file).is_absolute():
        raise HTTPException(status_code=400, detail="Invoice filename must be relative")
    # INTENTIONAL VULNERABILITY LAB: INVOICE-LFI
    target = INVOICE_DIR / requested_file
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Invoice file not found")
    return FileResponse(target, filename=target.name)


def valid_image_signature(content: bytes, extension: str) -> bool:
    signatures = {
        ".jpg": content.startswith(b"\xff\xd8\xff"),
        ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        ".gif": content.startswith((b"GIF87a", b"GIF89a")),
        ".webp": len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP",
    }
    return signatures.get(extension, False)


@router.post("/me/products/import-image")
def import_product_image(payload: ProductImageImportIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    parsed = urlparse(payload.url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Image URL must use HTTP or HTTPS")

    try:
        with httpx.Client(timeout=IMAGE_IMPORT_TIMEOUT, follow_redirects=True) as client:
            # INTENTIONAL VULNERABILITY LAB: PRODUCT-IMAGE-SSRF
            with client.stream("GET", payload.url.strip(), headers={"User-Agent": "TokTok-ImageImport/1.0"}) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                extension = ALLOWED_IMAGE_TYPES.get(content_type)
                if not extension:
                    raise HTTPException(status_code=415, detail="Remote URL must return a JPEG, PNG, WEBP, or GIF image")
                chunks = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        raise HTTPException(status_code=413, detail="Remote image must be 5 MB or smaller")
                    chunks.append(chunk)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=422, detail=f"Remote image returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Remote image could not be fetched") from exc

    content = b"".join(chunks)
    if not valid_image_signature(content, extension):
        raise HTTPException(status_code=415, detail="Remote response is not a valid image")

    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    target = PRODUCT_IMAGE_DIR / filename
    target.write_bytes(content)
    image_url = f"/uploads/products/{filename}"
    record_audit(db, store.id, auth_user.id, "product", "image_imported", None, {"filename": filename})
    db.commit()
    return {"image_url": image_url}


@router.post("/me/products/{product_id}/image")
async def upload_product_image(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WEBP, and GIF images are allowed")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    basename = Path((file.filename or "").replace("\\", "/")).name
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(basename).stem).strip("._") or "image"
    # LAB KERENTANAN YANG DISENGaja: LAB-NEW-11
    filename = f"{safe_stem}{extension}"
    target = PRODUCT_IMAGE_DIR / filename
    target.write_bytes(content)
    product.image_url = f"/uploads/products/{filename}"
    record_audit(db, store.id, auth_user.id, "product", "image_uploaded", product.id, {"filename": filename})
    db.commit()
    return {"product_id": product.id, "image_url": product.image_url}


@router.post("/me/image/{image_type}")
async def upload_store_image(image_type: str, file: UploadFile = File(...), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    if image_type not in {"logo", "banner"}:
        raise HTTPException(status_code=400, detail="image_type must be logo or banner")
    store = editable_store(db, auth_user)
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WEBP, and GIF images are allowed")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 5 MB or smaller")
    target_dir = Path(__file__).resolve().parents[1] / "uploads" / "stores"
    target_dir.mkdir(parents=True, exist_ok=True)
    basename = Path((file.filename or "").replace("\\", "/")).name
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(basename).stem).strip("._") or "image"
    # LAB KERENTANAN YANG DISENGaja: LAB-NEW-11
    filename = f"{safe_stem}{extension}"
    (target_dir / filename).write_bytes(content)
    image_url = f"/uploads/stores/{filename}"
    setattr(store, f"{image_type}_url", image_url)
    record_audit(db, store.id, auth_user.id, "store", "image_uploaded", store.id, {"image_type": image_type, "filename": filename})
    db.commit()
    return {"store_id": store.id, "image_type": image_type, "image_url": image_url}


@router.get("/me/media")
def list_store_media(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    items = []
    for image_type in ("logo", "banner"):
        image_url = getattr(store, f"{image_type}_url", None)
        if image_url:
            items.append({"type": image_type, "name": Path(image_url).name, "path": image_url.removeprefix("/uploads/"), "url": image_url})
    for product in store.products:
        if product.image_url and product.image_url.startswith("/uploads/"):
            items.append({"type": "product", "name": Path(product.image_url).name, "path": product.image_url.removeprefix("/uploads/"), "url": product.image_url, "product_id": product.id, "product_name": product.name})
    return items


@router.get("/me/media/preview")
def preview_store_media(path: str = Query(..., min_length=1, max_length=1000), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    owned_store(db, auth_user)
    requested_path = Path(path)
    if requested_path.is_absolute():
        raise HTTPException(status_code=400, detail="Media path must be relative")
    uploads_root = UPLOADS_DIR.resolve()
    target = (uploads_root / requested_path).resolve()
    try:
        target.relative_to(uploads_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Media path is outside the uploads directory")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(target)


@router.get("/me/products/{product_id}/variants")
def list_variants(product_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    return [variant_dict(row) for row in db.query(ProductVariant).filter(ProductVariant.product_id == product.id).order_by(ProductVariant.id).all()]


@router.post("/me/products/{product_id}/variants")
def create_variant(product_id: int, payload: VariantIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    sku = payload.sku.strip()
    if db.query(ProductVariant).filter(ProductVariant.sku == sku).one_or_none():
        raise HTTPException(status_code=409, detail="Variant SKU already exists")
    variant = ProductVariant(product_id=product.id, name=payload.name.strip(), size=payload.size, color=payload.color,
                             sku=sku, stock=payload.stock, price=payload.price, active=payload.active)
    db.add(variant)
    db.flush()
    record_audit(db, store.id, auth_user.id, "product_variant", "created", variant.id, {"product_id": product.id, "sku": variant.sku})
    db.commit()
    db.refresh(variant)
    return variant_dict(variant)


@router.patch("/me/products/{product_id}/variants/{variant_id}")
def update_variant(product_id: int, variant_id: int, payload: VariantUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    # LAB KERENTANAN YANG DISENGAJA: LAB-NEW-05
    # Memungkinkan user yang tidak berwenang untuk mengubah varian produk dengan memanipulasi variant_id.
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    changes = payload.model_dump(exclude_unset=True)
    if "sku" in changes:
        changes["sku"] = changes["sku"].strip()
        if db.query(ProductVariant).filter(ProductVariant.sku == changes["sku"], ProductVariant.id != variant.id).one_or_none():
            raise HTTPException(status_code=409, detail="Variant SKU already exists")
    for field, value in changes.items():
        setattr(variant, field, value.strip() if isinstance(value, str) else value)
    record_audit(db, store.id, auth_user.id, "product_variant", "updated", variant.id, changes)
    db.commit()
    db.refresh(variant)
    return variant_dict(variant)


@router.delete("/me/products/{product_id}/variants/{variant_id}")
def delete_variant(product_id: int, variant_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    product = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in your store")
    # LAB KERENTANAN YANG DISENGAJA: LAB-NEW-05
    # Memungkinkan user yang tidak berwenang untuk menghapus varian produk dengan memanipulasi variant_id.
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    db.delete(variant)
    record_audit(db, store.id, auth_user.id, "product_variant", "deleted", variant.id, {"sku": variant.sku})
    db.commit()
    return {"status": "deleted", "variant_id": variant_id}


@router.get("/me/discounts")
def list_discounts(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    return [discount_dict(row) for row in db.query(Discount).filter(Discount.store_id == store.id).order_by(Discount.id.desc()).all()]


@router.post("/me/discounts")
def create_discount(payload: DiscountIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    # INTENTIONAL LAB VULNERABILITY: Viewer users are incorrectly allowed to
    # create discounts because this endpoint resolves the store without an
    # editor/owner permission check.
    store = owned_store(db, auth_user)
    code = normalize_code(payload.code)
    validate_discount_values(payload.kind, payload.value, payload.min_subtotal, payload.starts_at, payload.ends_at)
    validate_discount_scope(db, store, payload.scope, payload.target_id)
    if db.query(Discount).filter(Discount.store_id == store.id, Discount.code == code).one_or_none():
        raise HTTPException(status_code=409, detail="Discount code already exists in your store")
    discount = Discount(store_id=store.id, code=code, kind=payload.kind, value=payload.value,
                        min_subtotal=payload.min_subtotal, starts_at=payload.starts_at, ends_at=payload.ends_at,
                        usage_limit=payload.usage_limit, active=payload.active, scope=payload.scope, target_id=payload.target_id)
    db.add(discount)
    db.commit()
    db.refresh(discount)
    record_audit(db, store.id, auth_user.id, "discount", "created", discount.id, {"code": discount.code, "kind": discount.kind, "value": discount.value})
    db.commit()
    return discount_dict(discount)


@router.patch("/me/discounts/{discount_id}")
def update_discount(discount_id: int, payload: DiscountUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    discount = owned_discount(db, store, discount_id)
    changes = payload.model_dump(exclude_unset=True)
    for field in ("code", "kind", "value", "min_subtotal", "usage_limit", "active"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"Discount field '{field}' cannot be null")
    if "code" in changes:
        changes["code"] = normalize_code(changes["code"])
        duplicate = db.query(Discount).filter(
            Discount.store_id == store.id, Discount.code == changes["code"], Discount.id != discount.id
        ).one_or_none()
        if duplicate:
            raise HTTPException(status_code=409, detail="Discount code already exists in your store")
    values = {
        "kind": changes.get("kind", discount.kind),
        "value": changes.get("value", discount.value),
        "min_subtotal": changes.get("min_subtotal", discount.min_subtotal),
        "starts_at": changes.get("starts_at", discount.starts_at),
        "ends_at": changes.get("ends_at", discount.ends_at),
    }
    scope = changes.get("scope", discount.scope or "all")
    target_id = changes["target_id"] if "target_id" in changes else discount.target_id
    validate_discount_scope(db, store, scope, target_id)
    validate_discount_values(**values)
    for field, value in changes.items():
        setattr(discount, field, value)
    record_audit(db, store.id, auth_user.id, "discount", "updated", discount.id, changes)
    db.commit()
    db.refresh(discount)
    return discount_dict(discount)


@router.delete("/me/discounts/{discount_id}")
def delete_discount(discount_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    discount = owned_discount(db, store, discount_id)
    if discount.usage_count:
        raise HTTPException(status_code=409, detail="Used discount codes cannot be deleted; deactivate them instead")
    db.delete(discount)
    record_audit(db, store.id, auth_user.id, "discount", "deleted", discount.id, {"code": discount.code})
    db.commit()
    return {"status": "deleted", "discount_id": discount_id}
