import logging
from typing import Iterable, Optional

from sqlmodel import Session, func, select

from app.models.user import Driver, DriverBase

logger = logging.getLogger(__name__)


class DriverRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, driver_data: DriverBase) -> Driver:
        try:
            driver = Driver.model_validate(driver_data)
            self.db.add(driver)
            self.db.commit()
            self.db.refresh(driver)
            return driver
        except Exception as exc:
            logger.error(f"Error creating driver: {exc}")
            self.db.rollback()
            raise

    def create_many(self, drivers: Iterable[Driver | DriverBase]) -> list[Driver]:
        created_drivers: list[Driver] = []
        try:
            for driver_data in drivers:
                driver = driver_data if isinstance(driver_data, Driver) else Driver.model_validate(driver_data)
                self.db.add(driver)
                created_drivers.append(driver)
            self.db.commit()
            for driver in created_drivers:
                self.db.refresh(driver)
            return created_drivers
        except Exception as exc:
            logger.error(f"Error creating drivers: {exc}")
            self.db.rollback()
            raise

    def get_all(self) -> list[Driver]:
        return list(self.db.exec(select(Driver)).all())

    def get_by_reservation_id(self, reservation_id: int) -> list[Driver]:
        statement = select(Driver).where(Driver.reservation_id == reservation_id)
        return list(self.db.exec(statement).all())

    def get_by_id(self, driver_id: int) -> Optional[Driver]:
        return self.db.get(Driver, driver_id)

    def update(self, driver_id: int, data: dict) -> Optional[Driver]:
        driver = self.db.get(Driver, driver_id)
        if not driver:
            return None

        for key, val in data.items():
            if val is not None:
                setattr(driver, key, val)

        try:
            self.db.add(driver)
            self.db.commit()
            self.db.refresh(driver)
            return driver
        except Exception as exc:
            logger.error(f"Error updating driver: {exc}")
            self.db.rollback()
            raise

    def delete(self, driver_id: int) -> None:
        driver = self.db.get(Driver, driver_id)
        if not driver:
            raise Exception("Driver not found")

        try:
            self.db.delete(driver)
            self.db.commit()
        except Exception as exc:
            logger.error(f"Error deleting driver: {exc}")
            self.db.rollback()
            raise

    def count(self) -> int:
        statement = select(func.count()).select_from(Driver)
        return int(self.db.exec(statement).one())
