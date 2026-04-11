from datetime import timezone

from fastapi import HTTPException, Request
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
)
from app.models.user import Reservation, VehicleReviewBase


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
    return reservation_repo.get_by_user_id(user.id)


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
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    if end_dt <= start_dt:
        raise HTTPException(status_code=400, detail="date_to must be after date_from")

    rental_days = max((end_dt - start_dt).days, 1)
    total_cost = float(vehicle.price_per_day) * rental_days

    reservation = Reservation(
        vehicle_id=vehicle.id,
        user_id=user.id,
        date_from=start_dt,
        date_to=end_dt,
        pickup_location=payload.pickup_location or vehicle.location,
        return_location=payload.return_location or vehicle.location,
        status="active",
        total_cost=total_cost,
        payment_method=payload.payment_method or "card",
        comment=payload.comment,
    )

    created = reservation_repo.create_many([reservation])[0]
    vehicle_repo.set_availability(vehicle.id, False)
    return created


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