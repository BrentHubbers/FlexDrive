from fastapi import HTTPException, Request
from sqlmodel import select
from app.dependencies import SessionDep, AuthDep, AdminDep
from . import api_router
from app.repositories.user import UserRepository
from app.repositories.vehicle import VehicleRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.vehicle_review import VehicleReviewRepository
from app.schemas import (
    UserResponse,
    VehicleResponse,
    ReservationCreate,
    ReservationResponse,
    AdminSummary,
    VehicleReviewCreate,
    VehicleReviewResponse,
    VehicleDetailResponse,
    AdminReservationUpdate,
    AdminVehicleCreate,
)
from app.models.user import Reservation, VehicleReviewBase, Vehicle


def _to_reservation_response(reservation: Reservation) -> ReservationResponse:
    return ReservationResponse(
        id=reservation.id,
        vehicle_id=reservation.vehicle_id,
        user_id=reservation.user_id,
        date_from=reservation.start_date,
        date_to=reservation.end_date,
        pickup_location=reservation.pickup_location,
        return_location=reservation.return_location,
        status=reservation.status,
        total_cost=reservation.total_cost,
    )


# API endpoint for listing users
@api_router.get("/users", response_model=list[UserResponse])
async def list_users(request: Request, db: SessionDep):
    user_repo = UserRepository(db)
    return user_repo.get_all_users()


@api_router.get("/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(db: SessionDep, location: str | None = None, available_only: bool = True):
    vehicle_repo = VehicleRepository(db)
    if available_only:
        vehicles = vehicle_repo.get_available(location=location)
    elif location:
        vehicles = vehicle_repo.get_by_location(location)
    else:
        vehicles = vehicle_repo.get_all_vehicles()

    response: list[VehicleResponse] = []
    for vehicle in vehicles:
        response.append(
            VehicleResponse(
                **vehicle.model_dump(),
            )
        )
    return response


@api_router.get("/vehicles/{vehicle_id}", response_model=VehicleDetailResponse)
async def get_vehicle_detail(vehicle_id: int, db: SessionDep):
    vehicle_repo = VehicleRepository(db)
    review_repo = VehicleReviewRepository(db)

    vehicle = vehicle_repo.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    reviews_raw = review_repo.get_by_vehicle_id(vehicle_id)
    reviews = [VehicleReviewResponse(**review.model_dump()) for review in reviews_raw]

    return VehicleDetailResponse(
        **vehicle.model_dump(),
        reviews=reviews,
    )


@api_router.get("/vehicles/{vehicle_id}/reviews", response_model=list[VehicleReviewResponse])
async def list_vehicle_reviews(vehicle_id: int, db: SessionDep):
    review_repo = VehicleReviewRepository(db)
    reviews = review_repo.get_by_vehicle_id(vehicle_id)
    return [VehicleReviewResponse(**review.model_dump()) for review in reviews]


@api_router.post("/vehicles/{vehicle_id}/reviews", response_model=VehicleReviewResponse)
async def create_vehicle_review(vehicle_id: int, payload: VehicleReviewCreate, db: SessionDep, user: AuthDep):
    vehicle_repo = VehicleRepository(db)
    review_repo = VehicleReviewRepository(db)

    vehicle = vehicle_repo.get_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    rating = max(1, min(5, int(payload.rating)))
    review = review_repo.create(
        vehicle_id=vehicle_id,
        review_data=VehicleReviewBase(rating=rating, comment=payload.comment, reviewer_name=user.username),
        user_id=user.id,
    )
    return VehicleReviewResponse(**review.model_dump())


@api_router.get("/vehicles/locations", response_model=list[str])
async def list_vehicle_locations(db: SessionDep):
    vehicle_repo = VehicleRepository(db)
    counts = vehicle_repo.count_by_location()
    return sorted(counts.keys())


@api_router.get("/my-reservations", response_model=list[ReservationResponse])
async def my_reservations(db: SessionDep, user: AuthDep):
    reservation_repo = ReservationRepository(db)
    reservations = reservation_repo.get_by_user_id(user.id)
    return [_to_reservation_response(reservation) for reservation in reservations]


@api_router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(payload: ReservationCreate, db: SessionDep, user: AuthDep):
    vehicle_repo = VehicleRepository(db)
    reservation_repo = ReservationRepository(db)

    vehicle = vehicle_repo.get_by_id(payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if not vehicle.available:
        raise HTTPException(status_code=400, detail="Vehicle is not available")

    start_dt = payload.date_from
    end_dt = payload.date_to

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="date_to must be after date_from")

    rental_days = max((end_dt - start_dt).days, 1)
    total_cost = float(vehicle.price_per_day) * rental_days

    reservation = Reservation(
        vehicle_id=vehicle.id,
        user_id=user.id,
        start_date=start_dt.date(),
        end_date=end_dt.date(),
        pickup_location=payload.pickup_location or vehicle.location,
        return_location=payload.return_location or vehicle.location,
        status="active",
        total_cost=total_cost,
        payment_method=payload.payment_method or "card",
        comment=payload.comment,
    )

    created = reservation_repo.create_many([reservation])[0]
    vehicle_repo.set_availability(vehicle.id, False)
    return _to_reservation_response(created)


@api_router.patch("/admin/reservations/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation_as_admin(reservation_id: int, db: SessionDep, _: AdminDep):
    reservation_repo = ReservationRepository(db)
    vehicle_repo = VehicleRepository(db)

    reservation = reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.status == "cancelled":
        return _to_reservation_response(reservation)

    reservation.status = "cancelled"
    updated = reservation_repo.update(reservation)
    vehicle_repo.set_availability(updated.vehicle_id, True)
    return _to_reservation_response(updated)


@api_router.get("/admin/reservations", response_model=list[ReservationResponse])
async def list_all_reservations_as_admin(db: SessionDep, _: AdminDep):
    reservation_repo = ReservationRepository(db)
    reservations = reservation_repo.get_all()
    return [_to_reservation_response(reservation) for reservation in reservations]


@api_router.patch("/admin/reservations/{reservation_id}", response_model=ReservationResponse)
async def edit_reservation_as_admin(
    reservation_id: int,
    payload: AdminReservationUpdate,
    db: SessionDep,
    _: AdminDep,
):
    reservation_repo = ReservationRepository(db)
    vehicle_repo = VehicleRepository(db)

    reservation = reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if payload.date_from is not None:
        reservation.start_date = payload.date_from.date()
    if payload.date_to is not None:
        reservation.end_date = payload.date_to.date()
    if reservation.end_date <= reservation.start_date:
        raise HTTPException(status_code=400, detail="date_to must be after date_from")

    if payload.pickup_location is not None:
        reservation.pickup_location = payload.pickup_location
    if payload.return_location is not None:
        reservation.return_location = payload.return_location

    if payload.status is not None:
        normalized_status = payload.status.strip().lower()
        if normalized_status not in {"active", "cancelled", "completed"}:
            raise HTTPException(status_code=400, detail="status must be active, cancelled, or completed")
        reservation.status = normalized_status

    updated = reservation_repo.update(reservation)

    if updated.status == "cancelled":
        vehicle_repo.set_availability(updated.vehicle_id, True)
    elif updated.status == "active":
        vehicle_repo.set_availability(updated.vehicle_id, False)

    return _to_reservation_response(updated)


@api_router.get("/admin/fleet", response_model=list[VehicleResponse])
async def list_fleet_as_admin(db: SessionDep, _: AdminDep):
    vehicle_repo = VehicleRepository(db)
    vehicles = vehicle_repo.get_all_vehicles()
    return [VehicleResponse(**vehicle.model_dump()) for vehicle in vehicles]


@api_router.post("/admin/fleet", response_model=VehicleResponse)
async def add_fleet_vehicle_as_admin(payload: AdminVehicleCreate, db: SessionDep, _: AdminDep):
    vehicle_repo = VehicleRepository(db)

    normalized_make = payload.make.strip()
    normalized_model = payload.model.strip()
    if not normalized_make or not normalized_model:
        raise HTTPException(status_code=400, detail="make and model are required")

    created = vehicle_repo.create(
        Vehicle(
            make=normalized_make,
            model=normalized_model,
            year=payload.year,
            color=(payload.color or "Unspecified").strip() or "Unspecified",
            license_plate=(payload.license_plate or f"ADM-{payload.year}-{normalized_make[:2].upper()}{normalized_model[:2].upper()}").strip(),
            category=payload.category.strip() or "Sedan",
            price_per_day=float(payload.price_per_day),
            available=bool(payload.available),
            location=payload.location.strip(),
            url_image=(payload.url_image or "https://via.placeholder.com/1200x800").strip(),
            exterior_image_url=(payload.exterior_image_url or payload.url_image or "https://via.placeholder.com/1200x800").strip(),
            interior_image_url=(payload.interior_image_url or payload.exterior_image_url or payload.url_image or "https://via.placeholder.com/1200x800").strip(),
            description=(payload.description or f"{normalized_make} {normalized_model} rental vehicle").strip(),
            seats=int(payload.seats or 5),
            transmission=(payload.transmission or "Automatic").strip(),
            fuel_type=(payload.fuel_type or "Petrol").strip(),
        )
    )
    return VehicleResponse(**created.model_dump())


@api_router.delete("/admin/fleet/{vehicle_id}")
async def remove_fleet_vehicle_as_admin(vehicle_id: int, db: SessionDep, _: AdminDep):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    active_reservation = db.exec(
        select(Reservation).where(
            (Reservation.vehicle_id == vehicle_id) & (Reservation.status == "active")
        )
    ).first()
    if active_reservation:
        raise HTTPException(status_code=400, detail="Cannot remove a vehicle with active reservations")

    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle removed"}


@api_router.get("/admin/summary", response_model=AdminSummary)
async def admin_summary(db: SessionDep, _: AdminDep):
    user_repo = UserRepository(db)
    vehicle_repo = VehicleRepository(db)
    reservation_repo = ReservationRepository(db)

    users = len(user_repo.get_all_users())
    vehicles = vehicle_repo.count()
    available_vehicles = len(vehicle_repo.get_available())
    reservations = reservation_repo.count()
    by_location = vehicle_repo.count_by_location()

    return AdminSummary(
        users=users,
        vehicles=vehicles,
        available_vehicles=available_vehicles,
        reservations=reservations,
        by_location=by_location,
    )