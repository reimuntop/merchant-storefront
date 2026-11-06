from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import Product, ProductQuestion, Review, User, get_db
from ..dependencies import require_authenticated_user, require_same_user
from ..schemas import ProductQuestionCreate, ReviewIn
from ..serializers import question_dict, review_dict
from ..services.reviews import has_purchased_product, has_reviewed_product

router = APIRouter(prefix="/api", tags=["reviews"])


@router.get("/products/{product_id}/questions")
def product_questions(product_id: int, db: Session = Depends(get_db), _: User = Depends(require_authenticated_user)):
    product = db.get(Product, product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found")
    rows = db.query(ProductQuestion).filter(ProductQuestion.product_id == product_id).order_by(ProductQuestion.id.desc()).all()
    return [question_dict(row) for row in rows]


@router.post("/products/{product_id}/questions")
def ask_product_question(product_id: int, payload: ProductQuestionCreate, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    product = db.get(Product, product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Product not found")
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Question cannot be blank")
    question = ProductQuestion(product_id=product_id, user_id=auth_user.id, message=payload.message)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question_dict(question)


@router.get("/products/{product_id}/reviews")
def product_reviews(product_id: str, db: Session = Depends(get_db), _: User = Depends(require_authenticated_user)):
    # INTENTIONAL LAB VULNERABILITY: product_id is interpolated into SQL.
    # Do not copy this pattern into production code; use a bound parameter instead.
    rows = db.query(Review).filter(
        text(f"reviews.product_id = {product_id}")
    ).order_by(Review.id.desc()).all()
    users = db.query(User).filter(User.id.in_({r.user_id for r in rows if not r.is_anonymous})).all() if rows else []
    names = {u.id: u.display_name for u in users}
    return [review_dict(row, names.get(row.user_id)) for row in rows]


@router.post("/reviews")
def api_add_review(payload: ReviewIn, db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, payload.user_id)
    if not db.get(Product, payload.product_id): raise HTTPException(status_code=404, detail="Product not found")
    if not has_purchased_product(db, payload.user_id, payload.product_id): raise HTTPException(status_code=403, detail="Only verified buyers can review this product")
    if has_reviewed_product(db, payload.user_id, payload.product_id): raise HTTPException(status_code=409, detail="You have already reviewed this product")
    review = Review(user_id=payload.user_id, product_id=payload.product_id, rating=payload.rating, body=payload.body, is_anonymous=payload.is_anonymous)
    db.add(review); db.commit(); db.refresh(review)
    return review_dict(review, auth_user.display_name)


@router.delete("/reviews/{review_id}")
def api_delete_review(review_id: int, user_id: int = Query(...), db: Session = Depends(get_db), auth_user: User = Depends(require_authenticated_user)):
    require_same_user(auth_user, user_id)
    raise HTTPException(status_code=403, detail="Reviews cannot be deleted after submission")
