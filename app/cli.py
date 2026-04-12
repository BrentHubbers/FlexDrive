from __future__ import annotations
import argparse
import csv
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
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

if __package__ is None or __package__ == "":
	sys.path.append(str(Path(__file__).resolve().parents[1]))


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
	{"username": "bob", "email": "bob@mail.com", "password": "bobpass", "role": "admin"},
	{"username": "admin", "email": "admin@trinirent.com", "password": "admin123", "role": "admin"},
	{"username": "customer1", "email": "customer1@trinirent.com", "password": "customer123", "role": "regular_user"},
	{"username": "customer2", "email": "customer2@trinirent.com", "password": "customer123", "role": "regular_user"},
]


# -------------------- CORE SETUP --------------------

def ensure_database_files() -> None:
	create_db_and_tables()
	DATABASE_FILE.touch(exist_ok=True)


def reset_database_schema() -> None:
	drop_all()
	create_db_and_tables()
	DATABASE_FILE.touch(exist_ok=True)


# -------------------- DEBUG HELPERS --------------------

def list_models() -> None:
	print("Loaded SQLModel tables:")
	for model in ALL_MODELS:
		table_name = getattr(model, "__tablename__", model.__name__.lower())
		print(f"- {model.__name__} (table: {table_name})")


def list_routes() -> None:
	print("Registered backend routes:")
	for route in app.routes:
		if isinstance(route, APIRoute):
			methods = ",".join(sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"}))
			print(f"- {methods:<8} {route.path}")


# -------------------- UTILITIES --------------------

def expand_location_plan() -> list[str]:
	locations = []
	for location, count in TRINIDAD_LOCATION_PLAN:
		locations.extend([location] * count)
	return locations


def parse_csv_bool(value: str | None, default: bool = True) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"true", "1", "yes", "y"}


def build_image_url(make: str, model: str, view: str) -> str:
	# 🔥 Stable image (no random failures)
	return "https://images.unsplash.com/photo-1549924231-f129b911e442?auto=format&fit=crop&w=1200&q=80"


# -------------------- VEHICLE LOADING --------------------

def load_demo_vehicle_data() -> list[VehicleBase]:
	locations = expand_location_plan()

	# 🔥 If CSV missing → generate data
	if not VEHICLES_CSV_PATH.exists():
		print("⚠️ vehicles.csv not found — generating demo vehicles...")

		demo = []
		for i, location in enumerate(locations):
			make = f"Brand{i+1}"
			model = f"Model{i+1}"

			demo.append(
				VehicleBase(
					make=make,
					model=model,
					year=2020,
					category="Sedan",
					price_per_day=250 + (i * 10),
					available=True,
					location=location,
					url_image=build_image_url(make, model, "ext"),
					exterior_image_url=build_image_url(make, model, "ext"),
					interior_image_url=build_image_url(make, model, "int"),
					description=f"{make} {model} is a reliable rental option.",
					seats=5,
					transmission="Automatic",
					fuel_type="Gasoline",
				)
			)

		return demo

	# ✅ CSV exists → use it
	with VEHICLES_CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
		rows = list(csv.DictReader(f))

	locations_needed = min(len(locations), len(rows))

	demo = []
	for row, location in zip(rows[:locations_needed], locations):
		make = row.get("make", "").strip()
		model = row.get("model", "").strip()

		demo.append(
			VehicleBase(
				make=make,
				model=model,
				year=int(row.get("year") or 2020),
				category=row.get("category") or "Sedan",
				price_per_day=float(row.get("price_per_day") or 250),
				available=parse_csv_bool(row.get("available")),
				location=location,
				url_image=row.get("url_image") or build_image_url(make, model, "ext"),
				exterior_image_url=row.get("exterior_image_url") or build_image_url(make, model, "ext"),
				interior_image_url=row.get("interior_image_url") or build_image_url(make, model, "int"),
				description=row.get("description") or f"{make} {model} is a great rental.",
				seats=int(row.get("seats") or 5),
				transmission=row.get("transmission") or "Automatic",
				fuel_type=row.get("fuel_type") or "Gasoline",
			)
		)

	return demo


# -------------------- SEEDING --------------------

def seed_users() -> int:
	created = 0
	with get_cli_session() as db:
		repo = UserRepository(db)
		for u in DEFAULT_USERS:
			if repo.get_by_username(u["username"]):
				continue
			repo.create(User(
				username=u["username"],
				email=u["email"],
				password=encrypt_password(u["password"]),
				role=u["role"]
			))
			created += 1
	return created


def seed_vehicles():
	with get_cli_session() as db:
		repo = VehicleRepository(db)

		if repo.count() > 0:
			return 0, repo.count_by_location()

		data = load_demo_vehicle_data()
		repo.create_many(data)
		return len(data), repo.count_by_location()


def seed_rental_activity():
	with get_cli_session() as db:
		res_repo = ReservationRepository(db)
		driver_repo = DriverRepository(db)
		comment_repo = CommentRepository(db)
		review_repo = VehicleReviewRepository(db)
		user_repo = UserRepository(db)
		vehicle_repo = VehicleRepository(db)

		if res_repo.count() > 0:
			return res_repo.count(), driver_repo.count(), comment_repo.count(), review_repo.count()

		users = user_repo.get_all_users()
		vehicles = vehicle_repo.get_all_vehicles()

		if not users or not vehicles:
			return 0, 0, 0, 0

		reservations = []
		for i, v in enumerate(vehicles[:8]):
			u = users[i % len(users)]
			start = datetime.now(timezone.utc) + timedelta(days=i + 1)
			end = start + timedelta(days=2)

			reservations.append(Reservation(
				vehicle_id=v.id,
				user_id=u.id,
				date_from=start,
				date_to=end,
				pickup_location=v.location,
				return_location=v.location,
				status="active",
				total_cost=v.price_per_day * 2,
				payment_method="card"
			))

		created_res = res_repo.create_many(reservations)

		drivers = []
		for i, r in enumerate(created_res):
			drivers.append(Driver(
				first_name=f"Driver{i+1}",
				phone=f"868555{i+100}",
				reservation_id=r.id
			))

		comments = [
			Comment(user_id=u.id, content=f"Feedback from {u.username}")
			for u in users
		]

		driver_repo.create_many(drivers)
		comment_repo.create_many(comments)

		for i, v in enumerate(vehicles[:10]):
			u = users[i % len(users)]
			review_repo.create(
				vehicle_id=v.id,
				review_data=VehicleReviewBase(
					rating=5,
					comment=f"Great car: {v.make} {v.model}",
					reviewer_name=u.username
				),
				user_id=u.id
			)

		return len(created_res), len(drivers), len(comments), 10


# -------------------- MAIN --------------------

def initialize_database():
	reset_database_schema()

	u = seed_users()
	v, counts = seed_vehicles()
	r, d, c, rev = seed_rental_activity()

	print(f"DB ready: {DATABASE_FILE}")
	print(f"Users: {u}, Vehicles: {v}, Reservations: {r}, Drivers: {d}, Comments: {c}, Reviews: {rev}")

	if counts:
		print("Vehicles by location:")
		for loc, count in counts.items():
			print(f"- {loc}: {count}")


def main():
	parser = argparse.ArgumentParser()
	sub = parser.add_subparsers(dest="cmd", required=True)

	sub.add_parser("initialize")
	sub.add_parser("list-models")
	sub.add_parser("list-routes")

	args = parser.parse_args()

	if args.cmd == "initialize":
		initialize_database()
	elif args.cmd == "list-models":
		ensure_database_files()
		list_models()
	elif args.cmd == "list-routes":
		list_routes()


if __name__ == "__main__":
	main()