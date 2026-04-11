import logging
from typing import Iterable

from sqlmodel import Session, func, select

from app.models.user import Driver


logger = logging.getLogger(__name__)


class DriverRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_many(self, drivers: Iterable[Driver]) -> list[Driver]:
        created_drivers: list[Driver] = []
        try:
            for driver in drivers:
                self.db.add(driver)
                created_drivers.append(driver)
            self.db.commit()
            for driver in created_drivers:
                self.db.refresh(driver)
            return created_drivers
        except Exception as exc:
            logger.error(f"An error occurred while saving drivers: {exc}")
            self.db.rollback()
            raise

    def count(self) -> int:
        statement = select(func.count()).select_from(Driver)
        return int(self.db.exec(statement).one())
