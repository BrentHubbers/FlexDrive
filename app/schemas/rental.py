from datetime import datetime
from sqlmodel import SQLModel


class VehicleResponse(SQLModel):
    id: int
    make: str
    model: str
    year: int
    license_plate: str
    category: str
    price_per_day: float
    available: bool
    location: str
    url_image: str | None = None
    exterior_image_url: str | None = None
    interior_image_url: str | None = None
    description: str | None = None
    seats: int | None = None
    transmission: str | None = None
    fuel_type: str | None = None


class ReservationCreate(SQLModel):
    vehicle_id: int
    date_from: datetime
    date_to: datetime
    pickup_location: str | None = None
    return_location: str | None = None
    payment_method: str | None = "card"
    comment: str | None = None


class ReservationResponse(SQLModel):
    id: int
    vehicle_id: int
    user_id: int | None = None
    date_from: datetime
    date_to: datetime
    pickup_location: str
    return_location: str
    status: str
    total_cost: float | None = None


class AdminSummary(SQLModel):
    users: int
    vehicles: int
    available_vehicles: int
    reservations: int
    by_location: dict[str, int]


class VehicleReviewCreate(SQLModel):
    rating: int
    comment: str


class VehicleReviewResponse(SQLModel):
    id: int
    vehicle_id: int
    user_id: int | None = None
    reviewer_name: str
    rating: int
    comment: str
    created_at: datetime


class VehicleDetailResponse(VehicleResponse):
    reviews: list[VehicleReviewResponse]


class AdminReservationUpdate(SQLModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    pickup_location: str | None = None
    return_location: str | None = None
    status: str | None = None


class AdminVehicleCreate(SQLModel):
    make: str
    model: str
    year: int
    category: str
    price_per_day: float
    location: str
    color: str | None = None
    license_plate: str | None = None
    url_image: str | None = None
    exterior_image_url: str | None = None
    interior_image_url: str | None = None
    description: str | None = None
    seats: int | None = None
    transmission: str | None = None
    fuel_type: str | None = None
    available: bool = True
