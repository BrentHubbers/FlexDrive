import logging
from typing import Optional

from sqlmodel import Session, func, select

from app.models.user import VehicleReview, VehicleReviewBase


logger = logging.getLogger(__name__)


class VehicleReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, vehicle_id: int, review_data: VehicleReviewBase, user_id: int | None = None) -> VehicleReview:
        try:
            review = VehicleReview(
                vehicle_id=vehicle_id,
                user_id=user_id,
                rating=review_data.rating,
                comment=review_data.comment,
                reviewer_name=review_data.reviewer_name,
            )
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)
            return review
        except Exception as exc:
            logger.error(f"An error occurred while saving vehicle review: {exc}")
            self.db.rollback()
            raise

    def get_by_vehicle_id(self, vehicle_id: int, include_hidden: bool = False) -> list[VehicleReview]:
        statement = select(VehicleReview).where(VehicleReview.vehicle_id == vehicle_id)
        if not include_hidden:
            statement = statement.where(VehicleReview.hidden == False)
        statement = statement.order_by(VehicleReview.pinned.desc(), VehicleReview.created_at.desc())
        return self.db.exec(statement).all()

    def get_all(self, include_hidden: bool = True) -> list[VehicleReview]:
        statement = select(VehicleReview)
        if not include_hidden:
            statement = statement.where(VehicleReview.hidden == False)
        statement = statement.order_by(VehicleReview.pinned.desc(), VehicleReview.created_at.desc())
        return self.db.exec(statement).all()

    def get_by_id(self, review_id: int) -> VehicleReview | None:
        return self.db.get(VehicleReview, review_id)

    def update(self, review: VehicleReview) -> VehicleReview:
        try:
            self.db.add(review)
            self.db.commit()
            self.db.refresh(review)
            return review
        except Exception as exc:
            logger.error(f"An error occurred while updating vehicle review: {exc}")
            self.db.rollback()
            raise

    def pin(self, review: VehicleReview, pinned: bool) -> VehicleReview:
        review.pinned = pinned
        return self.update(review)

    def hide(self, review: VehicleReview) -> VehicleReview:
        review.hidden = True
        review.pinned = False
        return self.update(review)

    def count(self) -> int:
        statement = select(func.count()).select_from(VehicleReview)
        return int(self.db.exec(statement).one())
