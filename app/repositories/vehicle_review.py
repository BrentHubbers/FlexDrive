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

    def get_by_vehicle_id(self, vehicle_id: int) -> list[VehicleReview]:
        statement = (
            select(VehicleReview)
            .where(VehicleReview.vehicle_id == vehicle_id)
            .order_by(VehicleReview.created_at.desc())
        )
        return self.db.exec(statement).all()

    def count(self) -> int:
        statement = select(func.count()).select_from(VehicleReview)
        return int(self.db.exec(statement).one())
