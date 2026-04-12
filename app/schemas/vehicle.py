from sqlmodel import SQLModel


class VehicleCreate(SQLModel):
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    category: str
    price_per_day: float
    location: str
    url_image: str | None = None
    exterior_image_url: str | None = None
    interior_image_url: str | None = None
    description: str | None = None
    seats: int
    transmission: str
    fuel_type: str
    available: bool = True


class VehicleUpdate(SQLModel):
    make: str | None = None
    model: str | None = None
    year: int | None = None
    color: str | None = None
    license_plate: str | None = None
    category: str | None = None
    price_per_day: float | None = None
    location: str | None = None
    url_image: str | None = None
    exterior_image_url: str | None = None
    interior_image_url: str | None = None
    description: str | None = None
    seats: int | None = None
    transmission: str | None = None
    fuel_type: str | None = None
    available: bool | None = None


class VehicleResponse(SQLModel):
    id: int
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    category: str
    price_per_day: float
    location: str
    url_image: str | None = None
    exterior_image_url: str | None = None
    interior_image_url: str | None = None
    description: str | None = None
    seats: int
    transmission: str
    fuel_type: str
    available: bool
