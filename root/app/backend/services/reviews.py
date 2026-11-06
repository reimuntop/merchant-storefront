from sqlalchemy.orm import Session

from ..database import Purchase, Review


def has_purchased_product(db: Session, user_id: int, product_id: int) -> bool:
    return db.query(Purchase).filter(Purchase.user_id == user_id, Purchase.product_id == product_id).first() is not None


def has_reviewed_product(db: Session, user_id: int, product_id: int) -> bool:
    return db.query(Review).filter(Review.user_id == user_id, Review.product_id == product_id).first() is not None


def delete_review(db: Session, review_id: int) -> bool:
    review = db.get(Review, review_id)
    if not review:
        return False
    db.delete(review)
    db.commit()
    return True
