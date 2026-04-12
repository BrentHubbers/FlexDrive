import csv
import pathlib
import sys
from datetime import date, timedelta

import typer
from sqlmodel import select

from app.database import get_cli_session, create_db_and_tables
from app.utilities.security import encrypt_password
from app.models.user import *

app = typer.Typer()

@app.command("initialize")
def init_db() -> None:
	
	trinidad_locations = [
		"Port of Spain",
		"San Fernando",
		"Chaguanas",
		"Arima",
		"Diego Martin",
		"Tunapuna",
		"Couva",
		"Point Fortin",
	]

	create_db_and_tables()

	with get_cli_session() as db:
		admin = db.exec(select(User).where(User.username == "admin")).one_or_none()
		if not admin:
			db.add(
				User(
					username="admin",
					email="admin@flexdrive.com",
					password=encrypt_password("adminpass"),
					role=UserRole.admin,
				)
			)
			print("Admin user created")
		elif admin.role != UserRole.admin:
			admin.role = UserRole.admin
			db.add(admin)
			print("Admin user role updated to admin")


		bob = db.exec(select(User).where(User.username == "bob")).one_or_none()
		if not bob:
			db.add(
				User(
					username="bob",
					email="bob@flexdrive.com",
					password=encrypt_password("bobpass"),
					role=UserRole.admin,
				)
			)
			print("Bob user created")
		elif bob.role != UserRole.admin:
			bob.role = UserRole.admin
			db.add(bob)
			print("Bob user role updated to admin")

		test_user = db.exec(select(User).where(User.username == "testuser")).one_or_none()
		if not test_user:
			db.add(
				User(
					username="testuser",
					email="testuser@flexdrive.com",
					password=encrypt_password("testpass"),
					role=UserRole.regular_user,
				)
			)
			print("Test user created")
		elif test_user.role != UserRole.regular_user:
			test_user.role = UserRole.regular_user
			db.add(test_user)
			print("Test user role updated to regular_user")

		invalid_users = db.exec(
			select(User).where((User.role != "admin") & (User.role != "regular_user"))
		).all()
		if invalid_users:
			invalid_names = ", ".join(user.username for user in invalid_users)
			raise ValueError(f"Invalid user role found for: {invalid_names}. Allowed roles: admin, regular_user")

		db.commit()

		# Sync vehicles from CSV every run (create new rows and update existing rows)
		rows: list[dict[str, str]] = []
		vehicles_csv_path = pathlib.Path("vehicles.csv")
		if not vehicles_csv_path.exists():
			vehicles_csv_path = pathlib.Path(__file__).resolve().parents[1] / "vehicles.csv"

		if vehicles_csv_path.exists():
			with open(vehicles_csv_path, "r", newline="", encoding="utf-8-sig") as file:
				reader = csv.DictReader(file)
				raw_rows = list(reader)

			if raw_rows:
				# Handle malformed first header like ",model,..." where make ends up unnamed.
				first_keys = [k for k in raw_rows[0].keys() if k is not None]
				first_key = first_keys[0] if first_keys else ""

				for row in raw_rows:
					cleaned = {
						str(k).strip(): ("" if v is None else str(v).strip())
						for k, v in row.items()
						if k is not None
					}
					make = cleaned.get("make", "")
					if not make and first_key in cleaned:
						make = cleaned.get(first_key, "")

					rows.append(
						{
							"make": make,
							"model": cleaned.get("model", ""),
							"year": cleaned.get("year", ""),
							"license_plate": cleaned.get("license_plate", ""),
							"category": cleaned.get("category", ""),
							"price_per_day": cleaned.get("price_per_day", ""),
							"available": cleaned.get("available", ""),
							"url_image": cleaned.get("url_image", ""),
							"exterior_image_url": cleaned.get("exterior_image_url", ""),
							"interior_image_url": cleaned.get("interior_image_url", ""),
							"description": cleaned.get("description", ""),
							"seats": cleaned.get("seats", ""),
							"transmission": cleaned.get("transmission", ""),
							"fuel_type": cleaned.get("fuel_type", ""),
						}
					)

		if not rows:
			print(f"{vehicles_csv_path} is missing or empty; no vehicles imported")
		else:
			vehicles_created = 0
			vehicles_updated = 0
			for index, row in enumerate(rows):
				make = (row.get("make") or "").strip() or "Unknown"
				model = (row.get("model") or "").strip() or "Model"
				category = (row.get("category") or "").strip() or "Sedan"
				url_image = (row.get("url_image") or "").strip() or "https://via.placeholder.com/1200x800"
				exterior_image_url = (row.get("exterior_image_url") or "").strip() or url_image
				interior_image_url = (row.get("interior_image_url") or "").strip() or exterior_image_url
				description = (row.get("description") or "").strip() or f"{make} {model} rental vehicle"
				transmission = (row.get("transmission") or "").strip() or "Automatic"
				fuel_type = (row.get("fuel_type") or "").strip() or "Petrol"

				year_raw = (row.get("year") or "").strip()
				try:
					year = int(float(year_raw)) if year_raw else 2022
				except ValueError:
					year = 2022

				price_raw = (row.get("price_per_day") or "").strip()
				try:
					price_per_day = float(price_raw) if price_raw else 200.0
				except ValueError:
					price_per_day = 200.0

				seats_raw = (row.get("seats") or "").strip()
				try:
					seats = int(float(seats_raw)) if seats_raw else 5
				except ValueError:
					seats = 5

				available_raw = (row.get("available") or "").strip().lower()
				available = True if not available_raw else available_raw in {"1", "true", "yes", "y", "on"}

				license_plate = (row.get("license_plate") or "").strip() or f"PBD-{index + 4:04d}"
				existing = db.exec(select(Vehicle).where(Vehicle.license_plate == license_plate)).one_or_none()

				if existing:
					existing.make = make
					existing.model = model
					existing.year = year
					existing.category = category
					existing.price_per_day = price_per_day
					existing.available = available
					existing.location = trinidad_locations[index % len(trinidad_locations)]
					existing.url_image = url_image
					existing.exterior_image_url = exterior_image_url
					existing.interior_image_url = interior_image_url
					existing.description = description
					existing.seats = seats
					existing.transmission = transmission
					existing.fuel_type = fuel_type
					db.add(existing)
					vehicles_updated += 1
				else:
					db.add(
						Vehicle(
							make=make,
							model=model,
							year=year,
							license_plate=license_plate,
							category=category,
							price_per_day=price_per_day,
							available=available,
							location=trinidad_locations[index % len(trinidad_locations)],
							url_image=url_image,
							exterior_image_url=exterior_image_url,
							interior_image_url=interior_image_url,
							description=description,
							seats=seats,
							transmission=transmission,
							fuel_type=fuel_type,
						)
					)
					vehicles_created += 1

			db.commit()
			print(
				f"Vehicle sync complete: {vehicles_created} created, {vehicles_updated} updated from {vehicles_csv_path.name}"
			)

	print("Database Initialized")


@app.command("clear-reservations")
def clear_reservations() -> None:
	"""Delete all reservations and linked drivers, and reset fleet availability."""
	confirm = typer.confirm("This will DELETE all reservations and linked drivers. Continue?")
	if not confirm:
		print("Cancelled.")
		return

	with get_cli_session() as db:
		for driver in db.exec(select(Driver)).all():
			db.delete(driver)

		for reservation in db.exec(select(Reservation)).all():
			db.delete(reservation)

		for vehicle in db.exec(select(Vehicle)).all():
			vehicle.available = True
			db.add(vehicle)

		db.commit()

	print("All reservations removed, drivers removed, and vehicle availability reset.")


@app.command("drop-db")
def drop_db() -> None:
	"""Drop all tables (destructive)."""
	confirm = typer.confirm("This will DELETE all data. Continue?")
	if confirm:
		from app.database import drop_all

		drop_all()
		print("All tables dropped.")


if __name__ == "__main__":
	app()
