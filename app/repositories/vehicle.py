import logging
from typing import Iterable, Optional

from sqlmodel import Session, func, select

from app.models.user import Vehicle, VehicleBase


logger = logging.getLogger(__name__)


class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, vehicle_data: VehicleBase) -> Optional[Vehicle]:
        try:
            vehicle_db = Vehicle.model_validate(vehicle_data)
            self.db.add(vehicle_db)
            self.db.commit()
            self.db.refresh(vehicle_db)
            return vehicle_db
        except Exception as exc:
            logger.error(f"An error occurred while saving vehicle: {exc}")
            self.db.rollback()
            raise

    def create_many(self, vehicles: Iterable[VehicleBase]) -> list[Vehicle]:
        created_vehicles: list[Vehicle] = []
        try:
            for vehicle_data in vehicles:
                vehicle_db = Vehicle.model_validate(vehicle_data)
                self.db.add(vehicle_db)
                created_vehicles.append(vehicle_db)
            self.db.commit()
            for vehicle_db in created_vehicles:
                self.db.refresh(vehicle_db)
            return created_vehicles
        except Exception as exc:
            logger.error(f"An error occurred while saving vehicles: {exc}")
            self.db.rollback()
            raise

    def get_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        return self.db.get(Vehicle, vehicle_id)

    def get_all_vehicles(self) -> list[Vehicle]:
        return self.db.exec(select(Vehicle)).all()

    def get_by_location(self, location: str) -> list[Vehicle]:
        normalized_location = location.strip().lower()
        statement = select(Vehicle).where(func.lower(func.trim(Vehicle.location)) == normalized_location)
        return self.db.exec(statement).all()

    def get_available(self, location: str | None = None) -> list[Vehicle]:
        statement = select(Vehicle).where(Vehicle.available == True)
        if location:
            normalized_location = location.strip().lower()
            statement = statement.where(func.lower(func.trim(Vehicle.location)) == normalized_location)
        return self.db.exec(statement).all()

    def set_availability(self, vehicle_id: int, available: bool) -> Vehicle:
        vehicle = self.db.get(Vehicle, vehicle_id)
        if not vehicle:
            raise Exception("Vehicle doesn't exist")
        try:
            vehicle.available = available
            self.db.add(vehicle)
            self.db.commit()
            self.db.refresh(vehicle)
            return vehicle
        except Exception as exc:
            logger.error(f"An error occurred while updating vehicle availability: {exc}")
            self.db.rollback()
            raise

    def count(self) -> int:
        statement = select(func.count()).select_from(Vehicle)
        return int(self.db.exec(statement).one())

    def count_by_location(self) -> dict[str, int]:
        statement = select(Vehicle.location, func.count()).group_by(Vehicle.location)
        return {location: int(total) for location, total in self.db.exec(statement).all()}

    def delete_all(self) -> None:
        try:
            statement = select(Vehicle)
            for vehicle in self.db.exec(statement).all():
                self.db.delete(vehicle)
            self.db.commit()
        except Exception as exc:
            logger.error(f"An error occurred while deleting vehicles: {exc}")
            self.db.rollback()
            raise