from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from sqlmodel import select
from app.dependencies import SessionDep, AuthDep, AdminDep
from . import api_router
from app.repositories.user import UserRepository
from app.repositories.vehicle import VehicleRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.vehicle_review import VehicleReviewRepository
from app.repositories.driver import DriverRepository
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
from app.models.user import Driver, Reservation, Vehicle, VehicleReviewBase


def _to_reservation_response(reservation: Reservation, driver_repo: DriverRepository | None = None) -> ReservationResponse:
    from app.schemas import DriverDetails

    driver_details = None
    if driver_repo and reservation.id:
        drivers = driver_repo.get_by_reservation_id(reservation.id)
        if drivers:
            driver_obj = drivers[0]
            driver_details = DriverDetails(
                first_name=driver_obj.first_name,
                last_name=driver_obj.last_name,
                email=driver_obj.email,
                phone=driver_obj.phone,
                address=driver_obj.address,
                city=driver_obj.city,
                state=driver_obj.state,
                license_num=driver_obj.license_num,
                license_expiry_date=driver_obj.license_to,
                license_from=driver_obj.license_from,
                license_to=driver_obj.license_to,
            )

    return ReservationResponse(
        id=reservation.id or 0,
        vehicle_id=reservation.vehicle_id or 0,
        user_id=reservation.user_id,
        date_from=datetime.combine(reservation.start_date, datetime.min.time()),
        date_to=datetime.combine(reservation.end_date, datetime.min.time()),
        pickup_location=reservation.pickup_location,
        return_location=reservation.return_location,
        status=reservation.status,
        total_cost=reservation.total_cost,
        protection_plan=reservation.protection_plan,
        flexible_rebooking=reservation.flexible_rebooking,
        created_at=reservation.created_at,
        driver=driver_details,
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


@api_router.get("/vehicles/locations", response_model=list[str])
async def list_vehicle_locations(db: SessionDep):
    vehicle_repo = VehicleRepository(db)
    counts = vehicle_repo.count_by_location()

    default_locations = [
        "Port of Spain",
        "San Fernando",
        "Chaguanas",
        "Arima",
        "Diego Martin",
        "Tunapuna",
        "Couva",
        "Point Fortin",
    ]

    db_locations = [location.strip() for location in counts.keys() if location and location.strip()]
    ordered_locations = list(default_locations)
    for location in sorted(db_locations):
        if location not in ordered_locations:
            ordered_locations.append(location)

    return ordered_locations


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


@api_router.get("/my-reservations", response_model=list[ReservationResponse])
async def my_reservations(db: SessionDep, user: AuthDep):
    reservation_repo = ReservationRepository(db)
    driver_repo = DriverRepository(db)
    reservations = reservation_repo.get_by_user_id(user.id or 0)
    return [_to_reservation_response(reservation, driver_repo) for reservation in reservations]


@api_router.patch("/reservations/{reservation_id}/cancel", response_model=dict)
async def cancel_my_reservation(reservation_id: int, db: SessionDep, user: AuthDep):
    reservation_repo = ReservationRepository(db)
    vehicle_repo = VehicleRepository(db)

    reservation = reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this reservation")

    if reservation.status == "cancelled":
        return {"message": "Reservation is already cancelled"}

    time_since_booking = datetime.utcnow() - reservation.created_at
    if time_since_booking > timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Cannot cancel reservation after 24 hours of booking")

    reservation.status = "cancelled"
    updated = reservation_repo.update(reservation)
    vehicle_repo.set_availability(updated.vehicle_id, True)

    return {"message": "Reservation cancelled successfully", "reservation_id": reservation_id}


@api_router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(payload: ReservationCreate, db: SessionDep, user: AuthDep):
    vehicle_repo = VehicleRepository(db)
    reservation_repo = ReservationRepository(db)
    driver_repo = DriverRepository(db)

    vehicle = vehicle_repo.get_by_id(payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    if not vehicle.available:
        raise HTTPException(status_code=400, detail="Vehicle is not available")

    if not payload.pickup_location or not payload.pickup_location.strip():
        raise HTTPException(status_code=400, detail="Please choose a pickup location.")

    if not payload.return_location or not payload.return_location.strip():
        raise HTTPException(status_code=400, detail="Please choose a return location.")

    if not payload.driver:
        raise HTTPException(status_code=400, detail="Driver information is required.")

    driver = payload.driver
    if not driver.first_name or not driver.first_name.strip():
        raise HTTPException(status_code=400, detail="First name is required.")
    if not driver.last_name or not driver.last_name.strip():
        raise HTTPException(status_code=400, detail="Last name is required.")
    if not driver.email or not str(driver.email).strip():
        raise HTTPException(status_code=400, detail="Email is required.")
    if not driver.phone or not driver.phone.strip():
        raise HTTPException(status_code=400, detail="Phone number is required.")
    if not driver.address or not driver.address.strip():
        raise HTTPException(status_code=400, detail="Address is required.")
    if not driver.city or not driver.city.strip():
        raise HTTPException(status_code=400, detail="City or province is required.")
    if not driver.license_num or not driver.license_num.strip():
        raise HTTPException(status_code=400, detail="License number is required.")
    if not driver.license_expiry_date:
        raise HTTPException(status_code=400, detail="License expiry date is required.")

    start_dt = payload.date_from
    end_dt = payload.date_to

    if start_dt.date() < datetime.utcnow().date():
        raise HTTPException(status_code=400, detail="Pickup date cannot be in the past.")

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="date_to must be after date_from")

    license_expiry_date = driver.license_expiry_date or driver.license_to
    if license_expiry_date and license_expiry_date <= start_dt.date():
        raise HTTPException(status_code=400, detail="License must still be valid on the pickup date.")

    rental_days = max((end_dt - start_dt).days, 1)
    total_cost = float(vehicle.price_per_day) * rental_days

    # Add protection plan cost ($30/day)
    if payload.protection_plan:
        total_cost += 30 * rental_days

    # Add flexible rebooking cost ($15 one-time)
    if payload.flexible_rebooking:
        total_cost += 15

    reservation = Reservation(
        vehicle_id=vehicle.id or 0,
        user_id=user.id,
        start_date=start_dt.date(),
        end_date=end_dt.date(),
        pickup_location=payload.pickup_location or vehicle.location,
        return_location=payload.return_location or vehicle.location,
        status="active",
        total_cost=total_cost,
        payment_method=payload.payment_method or "card",
        comment=payload.comment,
        protection_plan=payload.protection_plan,
        flexible_rebooking=payload.flexible_rebooking,
    )

    created = reservation_repo.create_many([reservation])[0]

    # Create driver record if driver details are provided
    if payload.driver and created.id:
        driver = Driver(
            first_name=driver.first_name,
            last_name=driver.last_name,
            email=driver.email,
            phone=driver.phone,
            address=driver.address,
            city=driver.city,
            state=driver.state,
            license_num=driver.license_num,
            license_from=driver.license_from,
            license_to=license_expiry_date,
            reservation_id=created.id,
        )
        driver_repo.create(driver)

    vehicle_repo.set_availability(vehicle.id or 0, False)
    return _to_reservation_response(created, driver_repo)


@api_router.patch("/admin/reservations/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation_as_admin(reservation_id: int, db: SessionDep, _: AdminDep):
    reservation_repo = ReservationRepository(db)
    vehicle_repo = VehicleRepository(db)
    driver_repo = DriverRepository(db)

    reservation = reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.status == "cancelled":
        return _to_reservation_response(reservation, driver_repo)

    reservation.status = "cancelled"
    updated = reservation_repo.update(reservation)
    vehicle_repo.set_availability(updated.vehicle_id, True)
    return _to_reservation_response(updated, driver_repo)


@api_router.get("/admin/reservations", response_model=list[ReservationResponse])
async def list_all_reservations_as_admin(db: SessionDep, _: AdminDep):
    reservation_repo = ReservationRepository(db)
    driver_repo = DriverRepository(db)
    reservations = reservation_repo.get_all()
    return [_to_reservation_response(reservation, driver_repo) for reservation in reservations]


@api_router.get("/admin/reviews", response_model=list[VehicleReviewResponse])
async def list_all_reviews_as_admin(db: SessionDep, _: AdminDep):
    review_repo = VehicleReviewRepository(db)
    reviews = review_repo.get_all(include_hidden=True)
    return [VehicleReviewResponse(**review.model_dump()) for review in reviews]


@api_router.patch("/admin/reviews/{review_id}/pin", response_model=VehicleReviewResponse)
async def pin_review_as_admin(review_id: int, db: SessionDep, _: AdminDep):
    review_repo = VehicleReviewRepository(db)
    review = review_repo.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    updated = review_repo.pin(review, not review.pinned)
    return VehicleReviewResponse(**updated.model_dump())


@api_router.delete("/admin/reviews/{review_id}")
async def remove_review_as_admin(review_id: int, db: SessionDep, _: AdminDep):
    review_repo = VehicleReviewRepository(db)
    review = review_repo.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review_repo.hide(review)
    return {"message": "Review removed"}


@api_router.patch("/admin/reservations/{reservation_id}", response_model=ReservationResponse)
async def edit_reservation_as_admin(
    reservation_id: int,
    payload: AdminReservationUpdate,
    db: SessionDep,
    _: AdminDep,
):
    reservation_repo = ReservationRepository(db)
    vehicle_repo = VehicleRepository(db)
    driver_repo = DriverRepository(db)

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

    return _to_reservation_response(updated, driver_repo)


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
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create vehicle")
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
    review_repo = VehicleReviewRepository(db)

    users = len(user_repo.get_all_users())
    vehicles = vehicle_repo.count()
    available_vehicles = len(vehicle_repo.get_available())
    reservations = reservation_repo.count()
    reviews = review_repo.count()
    by_location = vehicle_repo.count_by_location()

    return AdminSummary(
        users=users,
        vehicles=vehicles,
        available_vehicles=available_vehicles,
        reservations=reservations,
        reviews=reviews,
        by_location=by_location,
    )