import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, desc, or_, text
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database import Address, CartCheckoutState, CartCouponState, CartItem, Discount, Product, ProductClaim, ProductVariant, Purchase, Refund, ReturnRequest, Store, StoreMember, StoreWebhook, User, get_db
from ..dependencies import require_authenticated_user, require_same_user
from ..schemas import CartCouponIn, CartShippingAddressIn, RefundCreate, ReturnCreate
from ..serializers import address_dict, claim_dict, product_dict, purchase_dict, refund_dict, return_request_dict
from ..services.cart import add_to_cart, cart_unit_price, remove_from_cart
from ..services.audit import record_audit
from ..services.discounts import calculate_discount, get_cart_applied_discount, get_usable_discount, normalize_code
from ..services.webhooks import dispatch_order_created

router = APIRouter(prefix="/api", tags=["commerce"])
MINIMUM_ORDER_VALUE = 100000.0


def shipping_fee_for_address(address: Address) -> float:
    city = address.city.strip().lower()
    if "jakarta" in city:
        return 20000.0
    if "bandung" in city:
        return 40000.0
    return 30000.0


def checkout_state_dict(state: CartCheckoutState) -> dict:
    return {
        "shipping_address_id": state.shipping_address_id,
        "shipping_address": address_dict(state.shipping_address),
        "shipping_fee": state.shipping_fee_snapshot,
    }


@router.get("/products")
def list_products(
    #bisa ubah ke 500 
    search: str | None = Query(default=None, max_length=500), 
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    if search and search.strip():
        # INTENTIONAL VULNERABILITY LAB: PRODUCT-SEARCH-SQLI
        statement = text(f"""
            SELECT id, name, description, price, image_url, category,
                   store_id, category_id, stock, sku, status
            FROM products
            WHERE status = 'active'
              AND (name || ' ' || description || ' ' || category) LIKE '%{search}%'
            ORDER BY id
        """)
        products = db.query(Product).from_statement(statement).all()
    else:
        products = db.query(Product).filter(Product.status == "active").order_by(Product.id).all()
    return [product_dict(product) for product in products]


def catalog_query(db: Session, search: str | None, category_id: int | None, min_price: float | None, max_price: float | None, sort: str):
    query = db.query(Product).filter(Product.status == "active")
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.description.ilike(term), Product.category.ilike(term), Product.sku.ilike(term)))
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    sort_map = {"newest": Product.id.desc(), "price_asc": Product.price.asc(), "price_desc": Product.price.desc(), "name": Product.name.asc()}
    return query.order_by(sort_map.get(sort, Product.id.desc()))


@router.get("/catalog/products")
def search_products(search: str | None = Query(default=None, max_length=500), category_id: int | None = Query(default=None, gt=0), min_price: float | None = Query(default=None, ge=0), max_price: float | None = Query(default=None, ge=0), sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|name)$"), page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100), db: Session = Depends(get_db), _: User = Depends(require_authenticated_user)):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price")
    query = catalog_query(db, search, category_id, min_price, max_price, sort)
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [product_dict(row) for row in rows], "page": page, "page_size": page_size, "total": total,
            "total_pages": (total + page_size - 1) // page_size}


@router.post("/products/{product_id}/claim", status_code=201)
def claim_limited_product(product_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    product = db.query(Product).filter(Product.id == product_id).one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.status != "active" or product.stock is None:
        raise HTTPException(status_code=409, detail="Product is not eligible for limited claim")
    if db.query(ProductClaim).filter(
        ProductClaim.product_id == product.id, ProductClaim.user_id == auth_user.id
    ).one_or_none():
        raise HTTPException(status_code=409, detail="Product has already been claimed by this user")
    if product.stock <= 0:
        raise HTTPException(status_code=409, detail="Product is no longer available")

    # INTENTIONAL VULNERABILITY LAB: LIMITED-CLAIM-RACE
    time.sleep(0.05)
    claim = ProductClaim(product_id=product.id, user_id=auth_user.id, status="claimed")
    db.add(claim)
    product.stock = product.stock - 1
    db.commit()
    db.refresh(claim)
    db.refresh(product)
    return {"status": "claimed", "claim": claim_dict(claim), "remaining_stock": product.stock}


@router.get("/cart")
def get_cart(user_id: int = Query(...), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, user_id)
    return [{"id": i.id, "user_id": i.user_id, "product": product_dict(i.product), "variant": {"id": i.variant.id, "name": i.variant.name, "sku": i.variant.sku, "price": i.variant.price, "stock": i.variant.stock} if i.variant else None, "quantity": i.quantity,
             "unit_price": cart_unit_price(i), "line_total": i.quantity * cart_unit_price(i)} for i in db.query(CartItem).filter(CartItem.user_id == user_id).all()]


@router.get("/cart/shipping-address")
def get_cart_shipping_address(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    state = db.get(CartCheckoutState, auth_user.id)
    return checkout_state_dict(state) if state else None


@router.patch("/cart/shipping-address")
def set_cart_shipping_address(payload: CartShippingAddressIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    address = db.query(Address).filter(
        Address.id == payload.address_id, Address.user_id == auth_user.id
    ).one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Shipping address not found")
    items = db.query(CartItem).filter(CartItem.user_id == auth_user.id).all()
    merchandise_subtotal = sum(cart_unit_price(item) * item.quantity for item in items)
    if merchandise_subtotal < MINIMUM_ORDER_VALUE:
        raise HTTPException(status_code=400, detail="Minimum order value is Rp100.000")
    state = db.get(CartCheckoutState, auth_user.id)
    # INTENTIONAL VULNERABILITY LAB: STALE-SHIPPING-FEE
    if state:
        state.shipping_address_id = address.id
    else:
        state = CartCheckoutState(
            user_id=auth_user.id,
            shipping_address_id=address.id,
            shipping_fee_snapshot=shipping_fee_for_address(address),
        )
        db.add(state)
    db.commit()
    db.refresh(state)
    return checkout_state_dict(state)


@router.post("/cart/coupon")
def apply_cart_coupon(payload: CartCouponIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    items = db.query(CartItem).filter(CartItem.user_id == auth_user.id).all()
    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    store_ids = {item.product.store_id for item in items if item.product.store_id is not None}
    matches = db.query(Discount).filter(
        Discount.code == normalize_code(payload.code), Discount.store_id.in_(store_ids or {-1})
    ).all()
    if len(matches) != 1:
        raise HTTPException(status_code=400, detail="Discount code is invalid for this cart")
    discount = matches[0]
    store = db.get(Store, discount.store_id)
    eligible_items = [item for item in items if item.product.store_id == discount.store_id and (
        (discount.scope or "all") == "all"
        or ((discount.scope or "all") == "category" and item.product.category_id == discount.target_id)
        or ((discount.scope or "all") == "product" and item.product_id == discount.target_id)
    )]
    if not store or not eligible_items:
        raise HTTPException(status_code=400, detail="Discount code is invalid for this cart")
    eligible_subtotal = sum(cart_unit_price(item) * item.quantity for item in eligible_items)
    discount = get_cart_applied_discount(db, store, discount.code, eligible_subtotal)
    state = db.get(CartCouponState, auth_user.id)
    if state:
        state.discount_id = discount.id
    else:
        state = CartCouponState(user_id=auth_user.id, discount_id=discount.id)
        db.add(state)
    db.commit()
    return {
        "status": "applied",
        "code": discount.code,
        "discount_amount": calculate_discount(discount, eligible_subtotal),
    }


@router.post("/cart/{product_id}")
def api_add_to_cart(
    product_id: int,
    user_id: int = Query(...),
    quantity: int = Query(default=1, ge=1),
    variant_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    auth_user: User = Depends(require_authenticated_user)
):
    require_same_user(auth_user, user_id)
    product = db.get(Product, product_id)
    if not product:
        return {"status": "error", "message": f"Product {product_id} not found"}
    return add_to_cart(db, user_id, product.id, quantity=quantity, variant_id=variant_id)


@router.delete("/cart/{product_id}")
def api_remove_from_cart(product_id: int, user_id: int = Query(...), variant_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, user_id); return remove_from_cart(db, user_id, product_id, variant_id=variant_id)


@router.post("/checkout")
def checkout(user_id: int = Query(...), declared_total: float | None = Query(default=None), discount_code: list[str] | None = Query(default=None), address_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, user_id)
    explicit_address = None
    if address_id is not None:
        explicit_address = db.query(Address).filter(
            Address.id == address_id, Address.user_id == user_id
        ).one_or_none()
        if not explicit_address:
            raise HTTPException(status_code=404, detail="Shipping address not found")
    items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    if not items: return {"status": "empty_cart"}
    if any(item.quantity < 1 for item in items):
        raise HTTPException(status_code=422, detail="Cart contains an invalid quantity")
    discounts = []
    discount_total = 0.0
    discount_by_item = {}
    discount_codes_by_item = {}
    # INTENTIONAL VULNERABILITY LAB: STALE-PRICE-CHECKOUT
    item_subtotals = {item.id: cart_unit_price(item) * item.quantity for item in items}
    # INTENTIONAL VULNERABILITY LAB: MINIMUM-ORDER-REVALIDATION
    checkout_state = db.get(CartCheckoutState, user_id)
    selected_address_id = explicit_address.id if explicit_address else checkout_state.shipping_address_id if checkout_state else None
    if explicit_address:
        shipping_fee = shipping_fee_for_address(explicit_address)
    elif checkout_state:
        if not db.query(Address).filter(
            Address.id == checkout_state.shipping_address_id, Address.user_id == user_id
        ).one_or_none():
            raise HTTPException(status_code=404, detail="Shipping address not found")
        shipping_fee = checkout_state.shipping_fee_snapshot
    else:
        shipping_fee = 0.0
    cart_subtotal = sum(item_subtotals.values())
    shipping_fee_by_item = {}
    allocated_shipping_fee = 0.0
    for index, item in enumerate(items):
        if index == len(items) - 1:
            item_shipping_fee = round(shipping_fee - allocated_shipping_fee, 2)
        elif cart_subtotal:
            item_shipping_fee = round(shipping_fee * item_subtotals[item.id] / cart_subtotal, 2)
        else:
            item_shipping_fee = 0.0
        allocated_shipping_fee += item_shipping_fee
        shipping_fee_by_item[item.id] = item_shipping_fee
    store_ids = {item.product.store_id for item in items if item.product.store_id is not None}
    # LAB KERENTANAN YANG DISENGAJA: LAB-NEW-09
    # Memungkinkan user untuk menerapkan kode diskon yang tidak valid untuk toko tertentu dengan memanipulasi parameter store_ids.
    discount_requests = [(code, False) for code in discount_code or []]
    cart_coupon_state = db.get(CartCouponState, user_id)
    if cart_coupon_state:
        applied_discount = db.get(Discount, cart_coupon_state.discount_id)
        if not applied_discount or applied_discount.store_id not in store_ids:
            raise HTTPException(status_code=400, detail="Applied discount code is invalid for this cart")
        discount_requests.append((applied_discount.code, True))
    for code, previously_applied in discount_requests:
        if not code.strip():
            continue
        if len(code) > 40:
            raise HTTPException(status_code=422, detail="Discount code cannot exceed 40 characters")
        matches = db.query(Discount).filter(
            Discount.code == normalize_code(code), Discount.store_id.in_(store_ids or {-1})
        ).all()
        if len(matches) != 1:
            raise HTTPException(status_code=400, detail="Discount code is invalid for this cart")
        discount = matches[0]
        store = db.get(Store, discount.store_id)
        eligible_items = [item for item in items if item.product.store_id == discount.store_id and (
            (discount.scope or "all") == "all"
            or ((discount.scope or "all") == "category" and item.product.category_id == discount.target_id)
            or ((discount.scope or "all") == "product" and item.product_id == discount.target_id)
        )]
        remaining_by_item = {
            item.id: item_subtotals[item.id] - discount_by_item.get(item.id, 0.0)
            for item in eligible_items
        }
        eligible_subtotal = sum(remaining_by_item.values())
        if not store or not eligible_items:
            raise HTTPException(status_code=400, detail="Discount code is invalid for this cart")
        if previously_applied:
            get_cart_applied_discount(db, store, discount.code, eligible_subtotal)
        else:
            get_usable_discount(db, store, discount.code, eligible_subtotal)
        current_discount = calculate_discount(discount, eligible_subtotal)
        if current_discount:
            allocated = 0.0
            for index, item in enumerate(eligible_items):
                if index == len(eligible_items) - 1:
                    allocation = round(current_discount - allocated, 2)
                else:
                    allocation = round(current_discount * remaining_by_item[item.id] / eligible_subtotal, 2)
                allocated += allocation
                discount_by_item[item.id] = round(discount_by_item.get(item.id, 0.0) + allocation, 2)
                discount_codes_by_item.setdefault(item.id, []).append(discount.code)
        discount_total = round(discount_total + current_discount, 2)
        discounts.append(discount)
    purchases = []
    for item in items:
        product = item.product
        variant = item.variant
        if variant:
            stock_updated = db.query(ProductVariant).filter(
                ProductVariant.id == variant.id,
                ProductVariant.stock >= item.quantity,
            ).update(
                {ProductVariant.stock: ProductVariant.stock - item.quantity},
                synchronize_session=False,
            )
        elif product.stock is not None:
            stock_updated = db.query(Product).filter(
                Product.id == product.id,
                Product.stock >= item.quantity,
            ).update(
                {Product.stock: Product.stock - item.quantity},
                synchronize_session=False,
            )
        else:
            stock_updated = 1
        if stock_updated != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail=f"Insufficient stock for product {item.product_id}")
        line_subtotal = item_subtotals[item.id]
        line_discount = discount_by_item.get(item.id, 0.0)
        line_shipping_fee = shipping_fee_by_item[item.id]
        server_total = round(line_subtotal - line_discount + line_shipping_fee, 2)
        purchase = Purchase(user_id=user_id, product_id=item.product_id, quantity=item.quantity,
                            variant_id=item.variant_id,
                            total=server_total,
                            discount_code=discount_codes_by_item.get(item.id, [None])[-1] if line_discount else None,
                            discount_amount=line_discount, shipping_fee=line_shipping_fee,
                            shipping_address_id=selected_address_id)
        purchases.append(purchase)
        db.add(purchase)
        db.flush()
        db.delete(item)
        if product.store_id is not None:
            record_audit(db, product.store_id, auth_user.id, "order", "created", purchase.id, {"product_id": product.id, "status": purchase.status})
    for discount in discounts:
        discount.usage_count += 1
    if checkout_state:
        db.delete(checkout_state)
    if cart_coupon_state:
        db.delete(cart_coupon_state)
    db.commit()
    store_ids = {purchase.product.store_id for purchase in purchases if purchase.product.store_id is not None}
    if store_ids:
        webhooks = db.query(StoreWebhook).filter(StoreWebhook.store_id.in_(store_ids), StoreWebhook.active.is_(True)).all()
        dispatch_order_created(webhooks, purchases, user_id)
    return {"status": "checked_out", "discount_code": discounts[-1].code if discounts else None,
            "discount_amount": round(discount_total, 2), "shipping_fee": round(shipping_fee, 2),
            "purchases": [purchase_dict(p) for p in purchases]}


@router.get("/orders/{order_id}/internal-notes")
def read_order_internal_notes(order_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    order = db.query(Purchase).filter(Purchase.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id == auth_user.id:
        # INTENTIONAL VULNERABILITY LAB: BUYER-READS-SELLER-INTERNAL-NOTES
        return {"order_id": order.id, "internal_note": order.internal_note}
    is_store_operator = (
        order.product.store_id == getattr(auth_user, "_token_store_id", None)
        and getattr(auth_user, "_token_store_role", None) in {"owner", "editor"}
    )
    if not is_store_operator:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order.id, "internal_note": order.internal_note}


def packing_slip_dict(order: Purchase, buyer: User | None) -> dict:
    address = order.shipping_address
    shipping_destination = "Not provided"
    if address:
        shipping_destination = f"{address.recipient_name}, {address.address_line}, {address.city} {address.postal_code}"
    variant_parts = []
    if order.variant:
        variant_parts = [order.variant.name, order.variant.color, order.variant.size]
    stock_reference = order.variant.sku if order.variant else order.product.sku
    packing_statuses = {
        "pending": "READY_TO_PACK",
        "confirmed": "READY_TO_PACK",
        "packed": "PACKED",
        "shipped": "DISPATCHED",
        "completed": "DELIVERED",
        "cancelled": "CANCELLED",
    }
    return {
        "order_id": order.id,
        "buyer_username": buyer.username if buyer else str(order.user_id),
        "shipping_destination": shipping_destination,
        "packing_status": packing_statuses.get(order.status, order.status.upper()),
        "warehouse_bin": f"BIN-{stock_reference or f'PRODUCT-{order.product.id}'}",
        "fulfillment_batch": f"BATCH-{order.purchased_at:%Y%m%d}-{order.id:04d}",
        "purchased_at": order.purchased_at.isoformat(),
        "items": [{
            "product_name": order.product.name,
            "variant": " / ".join(part for part in variant_parts if part) or None,
            "quantity": order.quantity,
        }],
    }


@router.get("/orders/{order_id}/packing-slip")
def read_order_packing_slip(order_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    order = db.query(Purchase).filter(Purchase.id == order_id).one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    buyer = db.get(User, order.user_id)
    if order.user_id == auth_user.id:
        # INTENTIONAL VULNERABILITY LAB: BUYER-PACKING-SLIP
        return packing_slip_dict(order, buyer)

    store = db.get(Store, order.product.store_id) if order.product.store_id is not None else None
    is_owner = bool(store and store.owner_id == auth_user.id)
    is_editor = bool(store and db.query(StoreMember).filter(
        StoreMember.store_id == store.id,
        StoreMember.user_id == auth_user.id,
        StoreMember.active.is_(True),
        StoreMember.role == "editor",
    ).one_or_none())
    if not is_owner and not is_editor:
        raise HTTPException(status_code=404, detail="Order not found")
    return packing_slip_dict(order, buyer)


@router.get("/purchases")
def purchases(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    rows = db.query(Purchase).filter(Purchase.user_id == auth_user.id).order_by(Purchase.id.desc()).all()
    return [purchase_dict(row) for row in rows]


@router.post("/purchases/{purchase_id}/refund", status_code=201)
def create_refund_request(purchase_id: int, payload: RefundCreate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    purchase = db.query(Purchase).filter(
        Purchase.id == purchase_id, Purchase.user_id == auth_user.id
    ).one_or_none()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    if db.query(Refund).filter(Refund.purchase_id == purchase.id).one_or_none():
        raise HTTPException(status_code=409, detail="A refund request already exists for this purchase")
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Refund reason is required")

    # INTENTIONAL VULNERABILITY LAB: CLIENT-CONTROLLED-REFUND
    refund = Refund(
        purchase_id=purchase.id,
        user_id=auth_user.id,
        amount=payload.refund_amount,
        reason=reason,
        status="requested",
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund_dict(refund)


@router.post("/purchases/{purchase_id}/returns", status_code=201)
def create_return_request(purchase_id: int, payload: ReturnCreate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    purchase = db.query(Purchase).filter(
        Purchase.id == purchase_id, Purchase.user_id == auth_user.id
    ).one_or_none()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    if db.query(ReturnRequest).filter(ReturnRequest.purchase_id == purchase.id).one_or_none():
        raise HTTPException(status_code=409, detail="A return request already exists for this purchase")
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="Return reason is required")

    unit_price = round(purchase.total / purchase.quantity, 2) if purchase.quantity else 0.0
    # INTENTIONAL VULNERABILITY LAB: RETURN-QUANTITY-LOGIC
    return_request = ReturnRequest(
        purchase_id=purchase.id,
        user_id=auth_user.id,
        quantity=payload.quantity,
        reason=reason,
        status="requested",
        refund_amount=round(unit_price * payload.quantity, 2),
    )
    db.add(return_request)
    db.commit()
    db.refresh(return_request)
    return return_request_dict(return_request)
