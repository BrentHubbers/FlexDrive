from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone

if __package__ is None or __package__ == "":
	# Allow running as `python app/cli.py ...` by adding project root to sys.path.
	sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.routing import APIRoute

from app.database import create_db_and_tables, drop_all, get_cli_session
from app.main import app
from app.models.user import Comment, Driver, Reservation, User, Vehicle, VehicleBase, VehicleReview, VehicleReviewBase
from app.repositories.user import UserRepository
from app.repositories.vehicle import VehicleRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.driver import DriverRepository
from app.repositories.comment import CommentRepository
from app.repositories.vehicle_review import VehicleReviewRepository
from app.utilities.security import encrypt_password


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VEHICLES_CSV_PATH = PROJECT_ROOT / "vehicles.csv"
DATABASE_FILE = PROJECT_ROOT / "database.db"

TRINIDAD_LOCATION_PLAN = [
	("Port of Spain", 4),
	("San Fernando", 4),
	("Chaguanas", 4),
	("Arima", 3),
	("Diego Martin", 3),
	("Tunapuna", 3),
	("Couva", 2),
	("Point Fortin", 2),
]

ALL_MODELS = [User, Vehicle, Reservation, Driver, Comment, VehicleReview]

DEFAULT_USERS = [
	{
		"username": "bob",
		"email": "bob@mail.com",
		"password": "bobpass",
		"role": "admin",
	},
	{
		"username": "admin",
		"email": "admin@trinirent.com",
		"password": "admin123",
		"role": "admin",
	},
	{
		"username": "customer1",
		"email": "customer1@trinirent.com",
		"password": "customer123",
		"role": "regular_user",
	},
	{
		"username": "customer2",
		"email": "customer2@trinirent.com",
		"password": "customer123",
		"role": "regular_user",
	},
]


def ensure_database_files() -> None:
	create_db_and_tables()
	DATABASE_FILE.touch(exist_ok=True)


def reset_database_schema() -> None:
	drop_all()
	create_db_and_tables()
	DATABASE_FILE.touch(exist_ok=True)


def list_models() -> None:
	print("Loaded SQLModel tables:")
	for model in ALL_MODELS:
		table_name = getattr(model, "__tablename__", model.__name__.lower())
		print(f"- {model.__name__} (table: {table_name})")


def list_routes() -> None:
	print("Registered backend routes from app.main:app")
	for route in app.routes:
		if isinstance(route, APIRoute):
			methods = ",".join(sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"}))
			print(f"- {methods:<8} {route.path} -> {route.name}")


def expand_location_plan() -> list[str]:
	locations: list[str] = []
	for location, count in TRINIDAD_LOCATION_PLAN:
		locations.extend([location] * count)
	return locations


def parse_csv_bool(value: str | None, default: bool = True) -> bool:
	if value is None:
		return default
	lowered = value.strip().lower()
	if lowered in {"true", "1", "yes", "y"}:
		return True
	if lowered in {"false", "0", "no", "n"}:
		return False
	return default


def build_image_url(make: str, model: str, view: str) -> str:
	query = f"{make} {model} car {view}".strip().replace(" ", "+")
	return f"https://source.unsplash.com/random/1200x800/?{query}"


def load_demo_vehicle_data() -> list[VehicleBase]:
	if not VEHICLES_CSV_PATH.exists():
		raise FileNotFoundError(f"Missing vehicles source file: {VEHICLES_CSV_PATH}")

	locations = expand_location_plan()
	with VEHICLES_CSV_PATH.open(newline="", encoding="utf-8-sig") as csv_file:
		reader = csv.DictReader(csv_file)
		rows = list(reader)

	needed = len(locations)
	if len(rows) < needed:
		raise RuntimeError(f"vehicles.csv has {len(rows)} rows, but {needed} rows are required")

	demo_vehicles: list[VehicleBase] = []
	for row, location in zip(rows[:needed], locations):
		make = (row.get("make") or "").strip()
		model = (row.get("model") or "").strip()
		demo_vehicles.append(
			VehicleBase(
				make=make,
				model=model,
				year=int(row.get("year") or 0),
				category=(row.get("category") or "").strip(),
				price_per_day=float(row.get("price_per_day") or 0.0),
				available=parse_csv_bool(row.get("available"), default=True),
				location=location,
				url_image=((row.get("url_image") or "").strip() or build_image_url(make, model, "exterior")),
				exterior_image_url=((row.get("exterior_image_url") or "").strip() or build_image_url(make, model, "exterior")),
				interior_image_url=((row.get("interior_image_url") or "").strip() or build_image_url(make, model, "interior")),
				description=((row.get("description") or "").strip() or f"{make} {model} is a comfortable rental choice for Trinidad roads."),
				seats=int(row.get("seats") or 5),
				transmission=((row.get("transmission") or "").strip() or "Automatic"),
				fuel_type=((row.get("fuel_type") or "").strip() or "Gasoline"),
			)
		)

	return demo_vehicles


def seed_users() -> int:
	created = 0
	with get_cli_session() as db:
		user_repo = UserRepository(db)
		for user_data in DEFAULT_USERS:
			existing = user_repo.get_by_username(user_data["username"])
			if existing:
				continue

			user_repo.create(
				User(
					username=user_data["username"],
					email=user_data["email"],
					password=encrypt_password(user_data["password"]),
					role=user_data["role"],
				)
			)
			created += 1

	return created


def seed_vehicles() -> tuple[int, dict[str, int]]:
	with get_cli_session() as db:
		vehicle_repo = VehicleRepository(db)
		existing_count = vehicle_repo.count()

		if existing_count > 0:
			return 0, vehicle_repo.count_by_location()

		demo_vehicles = load_demo_vehicle_data()
		vehicle_repo.create_many(demo_vehicles)
		counts = vehicle_repo.count_by_location()
		return len(demo_vehicles), counts


def seed_rental_activity() -> tuple[int, int, int, int]:
	with get_cli_session() as db:
		reservation_repo = ReservationRepository(db)
		driver_repo = DriverRepository(db)
		comment_repo = CommentRepository(db)
		vehicle_review_repo = VehicleReviewRepository(db)
		user_repo = UserRepository(db)
		vehicle_repo = VehicleRepository(db)

		if reservation_repo.count() > 0:
			return reservation_repo.count(), driver_repo.count(), comment_repo.count(), vehicle_review_repo.count()

		users = user_repo.get_all_users()
		vehicles = vehicle_repo.get_all_vehicles()

		if not users or not vehicles:
			return 0, 0, 0, 0

		reservation_records: list[Reservation] = []
		for index, vehicle in enumerate(vehicles[:8]):
			assigned_user = users[index % len(users)]
			start_dt = datetime.now(timezone.utc) + timedelta(days=index + 1)
			end_dt = start_dt + timedelta(days=2)
			reservation_records.append(
				Reservation(
					vehicle_id=vehicle.id,
					user_id=assigned_user.id,
					date_from=start_dt,
					date_to=end_dt,
					pickup_location=vehicle.location,
					return_location=vehicle.location,
					status="active",
					total_cost=vehicle.price_per_day * 2,
					payment_method="card",
					comment="Seeded reservation",
				)
			)

		created_reservations = reservation_repo.create_many(reservation_records)

		driver_records: list[Driver] = []
		for index, reservation in enumerate(created_reservations):
			driver_records.append(
				Driver(
					first_name=f"Driver{index + 1}",
					last_name="Seed",
					email=f"driver{index + 1}@trinirent.com",
					phone=f"8685550{100 + index}",
					country="Trinidad and Tobago",
					city=reservation.pickup_location,
					license_num=f"L-{100000 + index}",
					reservation_id=reservation.id,
				)
			)

		comment_records: list[Comment] = []
		for index, user in enumerate(users):
			comment_records.append(
				Comment(
					user_id=user.id,
					content=f"Seed feedback #{index + 1}: booking flow for {user.username} is ready.",
				)
			)

		created_drivers = driver_repo.create_many(driver_records)
		created_comments = comment_repo.create_many(comment_records)

		review_count = 0
		for index, vehicle in enumerate(vehicles[:10]):
			user = users[index % len(users)]
			vehicle_review_repo.create(
				vehicle_id=vehicle.id,
				review_data=VehicleReviewBase(
					rating=5 - (index % 2),
					comment=f"Great drive quality and clean interior for the {vehicle.make} {vehicle.model}.",
					reviewer_name=user.username,
				),
				user_id=user.id,
			)
			review_count += 1

		return len(created_reservations), len(created_drivers), len(created_comments), review_count


def initialize_database() -> None:
	reset_database_schema()

	users_created = seed_users()
	vehicles_created, vehicle_counts = seed_vehicles()
	reservations_count, drivers_count, comments_count, review_count = seed_rental_activity()

	print(f"Database file ready: {DATABASE_FILE}")
	print(f"Users created: {users_created}")
	print(f"Vehicles created from vehicles.csv: {vehicles_created}")
	print(f"Reservations available: {reservations_count}")
	print(f"Drivers available: {drivers_count}")
	print(f"Comments available: {comments_count}")
	print(f"Vehicle reviews available: {review_count}")

	if vehicle_counts:
		print("Vehicle inventory by Trinidad location:")
		for location, count in sorted(vehicle_counts.items()):
			print(f"- {location}: {count}")


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Repository-driven CLI for database setup and inspection.")
	subparsers = parser.add_subparsers(dest="command", required=True)

	subparsers.add_parser("initialize", help="Create database.db and seed repository data from vehicles.csv.")
	subparsers.add_parser("init-db", help="Alias for initialize.")
	subparsers.add_parser("list-models", help="List SQLModel tables.")
	subparsers.add_parser("list-routes", help="List backend routes registered in app.main.")

	return parser


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()

	if args.command in {"initialize", "init-db"}:
		initialize_database()
		return

	if args.command == "list-models":
		ensure_database_files()
		list_models()
		return

	if args.command == "list-routes":
		list_routes()
		return

	parser.print_help()


if __name__ == "__main__":
	main()
