import logging
from typing import Iterable, Optional

from sqlmodel import Session, func, select

from app.models.user import Reservation, ReservationBase


logger = logging.getLogger(__name__)


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, reservation_data: ReservationBase, user_id: int | None = None) -> Optional[Reservation]:
        try:
            reservation_db = Reservation.model_validate(reservation_data)
            reservation_db.user_id = user_id
            self.db.add(reservation_db)
            self.db.commit()
            self.db.refresh(reservation_db)
            return reservation_db
        except Exception as exc:
            logger.error(f"An error occurred while saving reservation: {exc}")
            self.db.rollback()
            raise

    def create_many(self, reservations: Iterable[Reservation]) -> list[Reservation]:
        created_reservations: list[Reservation] = []
        try:
            for reservation in reservations:
                self.db.add(reservation)
                created_reservations.append(reservation)
            self.db.commit()
            for reservation in created_reservations:
                self.db.refresh(reservation)
            return created_reservations
        except Exception as exc:
            logger.error(f"An error occurred while saving reservations: {exc}")
            self.db.rollback()
            raise

    def get_all(self) -> list[Reservation]:
        return self.db.exec(select(Reservation)).all()

    def get_by_user_id(self, user_id: int) -> list[Reservation]:
        statement = select(Reservation).where(Reservation.user_id == user_id)
        return self.db.exec(statement).all()

    def get_by_id(self, reservation_id: int) -> Optional[Reservation]:
        return self.db.get(Reservation, reservation_id)

    def update(self, reservation: Reservation) -> Reservation:
        try:
            self.db.add(reservation)
            self.db.commit()
            self.db.refresh(reservation)
            return reservation
        except Exception as exc:
            logger.error(f"An error occurred while updating reservation: {exc}")
            self.db.rollback()
            raise

    def count(self) -> int:
        statement = select(func.count()).select_from(Reservation)
        return int(self.db.exec(statement).one())
