import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import Address, AuditLog, Product, ProductQuestion, Purchase, Review, Store, User, get_db
from ..dependencies import require_authenticated_user
from ..schemas import AddressIn, AddressUpdate, ProductQuestionAnswer
from ..serializers import address_dict, question_dict, review_dict
from ..services.audit import record_audit
from .stores import editable_store, owned_store

router = APIRouter(tags=["store operations"])


@router.get("/api/stores/me/questions")
def store_questions(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    rows = db.query(ProductQuestion).join(Product).filter(Product.store_id == store.id).order_by(ProductQuestion.id.desc()).all()
    return [question_dict(row) for row in rows]


@router.patch("/api/stores/me/questions/{question_id}/answer")
def answer_product_question(question_id: int, payload: ProductQuestionAnswer, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = editable_store(db, auth_user)
    question = db.query(ProductQuestion).join(Product).filter(
        ProductQuestion.id == question_id, Product.store_id == store.id
    ).one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in your store")
    if not payload.answer.strip():
        raise HTTPException(status_code=422, detail="Answer cannot be blank")
    question.answer = payload.answer
    question.answered_at = datetime.utcnow()
    db.commit()
    db.refresh(question)
    return question_dict(question)


@router.get("/api/me/addresses")
def list_addresses(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    return [address_dict(row) for row in db.query(Address).filter(Address.user_id == auth_user.id).order_by(Address.is_default.desc(), Address.id).all()]


@router.post("/api/me/addresses")
def create_address(payload: AddressIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    if payload.is_default:
        db.query(Address).filter(Address.user_id == auth_user.id).update({Address.is_default: False}, synchronize_session=False)
    address = Address(user_id=auth_user.id, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address_dict(address)


def address_by_id(db: Session, address_id: int) -> Address | None:
    # INTENTIONAL VULNERABILITY LAB: SAVED-ADDRESS-IDOR
    return db.query(Address).filter(Address.id == address_id).one_or_none()


@router.get("/api/me/addresses/{address_id}")
def get_address(address_id: int, db: Session = Depends(get_db), _: User = Depends(require_authenticated_user)):
    address = address_by_id(db, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address_dict(address)


@router.patch("/api/me/addresses/{address_id}")
def update_address(address_id: int, payload: AddressUpdate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    address = address_by_id(db, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    if payload.is_default:
        db.query(Address).filter(Address.user_id == address.user_id, Address.id != address.id).update({Address.is_default: False}, synchronize_session=False)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(address, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(address)
    return address_dict(address)


@router.delete("/api/me/addresses/{address_id}")
def delete_address(address_id: int, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    address = db.query(Address).filter(Address.id == address_id, Address.user_id == auth_user.id).one_or_none()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(address)
    db.commit()
    return {"status": "deleted", "address_id": address_id}


@router.get("/api/stores/me/customers")
def list_store_customers(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    rows = db.query(User.id, User.username, User.display_name, func.count(Purchase.id), func.coalesce(func.sum(Purchase.total), 0)).join(
        Purchase, Purchase.user_id == User.id
    ).join(Product, Purchase.product_id == Product.id).filter(Product.store_id == store.id).group_by(
        User.id, User.username, User.display_name
    ).order_by(func.count(Purchase.id).desc()).all()
    return [{"id": row[0], "username": row[1], "display_name": row[2], "order_count": row[3], "total_spent": row[4]} for row in rows]


@router.get("/api/stores/me/analytics/sales")
def sales_dashboard(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    base = db.query(Purchase).join(Product, Purchase.product_id == Product.id).filter(Product.store_id == store.id)
    total_sales = db.query(func.coalesce(func.sum(Purchase.total), 0)).join(Product, Purchase.product_id == Product.id).filter(Product.store_id == store.id).scalar()
    order_count = base.with_entities(func.count(func.distinct(Purchase.id))).scalar()
    top_rows = db.query(Product.id, Product.name, func.sum(Purchase.quantity).label("units"), func.sum(Purchase.total).label("revenue")).join(
        Purchase, Purchase.product_id == Product.id
    ).filter(Product.store_id == store.id).group_by(Product.id, Product.name).order_by(func.sum(Purchase.quantity).desc()).limit(10).all()
    return {
        "total_sales": total_sales,
        "order_count": order_count,
        "top_products": [{"product_id": row[0], "name": row[1], "units_sold": row[2], "revenue": row[3]} for row in top_rows],
    }


@router.get("/api/stores/me/reviews")
def list_store_reviews(db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    rows = db.query(Review, Product, User).join(
        Product, Review.product_id == Product.id
    ).outerjoin(
        User, Review.user_id == User.id
    ).filter(Product.store_id == store.id).order_by(Review.created_at.desc(), Review.id.desc()).all()
    average_rating = db.query(func.avg(Review.rating)).join(
        Product, Review.product_id == Product.id
    ).filter(Product.store_id == store.id).scalar()
    return {
        "items": [
            {
                **review_dict(review, user.display_name if user else None),
                "product_name": product.name,
            }
            for review, product, user in rows
        ],
        "review_count": len(rows),
        "average_rating": round(float(average_rating), 1) if average_rating is not None else 0,
    }


@router.get("/api/stores/me/audit-logs")
def list_audit_logs(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    store = owned_store(db, auth_user)
    query = db.query(AuditLog).filter(AuditLog.store_id == store.id).order_by(AuditLog.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": row.id, "actor_user_id": row.actor_user_id, "entity_type": row.entity_type,
                       "entity_id": row.entity_id, "action": row.action,
                       "changes": json.loads(row.changes) if row.changes else None,
                       "created_at": row.created_at.isoformat()} for row in rows], "page": page,
            "page_size": page_size, "total": total}
