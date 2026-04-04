from datetime import datetime, date
from typing import Optional, List, Dict
from pydantic import EmailStr
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: EmailStr = Field(index=True, unique=True)
    password: str
    role: str = "regular_user"


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


class ReservationBase(SQLModel):
    vehicle_id: int
    date_from: datetime
    date_to: datetime
    pickup_location: str
    return_location: str
    insurance_id: Optional[int] = None
    extras: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON))
    payment_method: Optional[str] = None
    comment: Optional[str] = None
    authorized_user_id: Optional[int] = None


class Reservation(ReservationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")


class DriverBase(SQLModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: str
    country: Optional[str] = None
    zip: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    building: Optional[str] = None
    birthday: Optional[date] = None
    notes: Optional[str] = None
    license_num: Optional[str] = None
    license_from: Optional[date] = None
    license_to: Optional[date] = None
    code: Optional[str] = None
    license_photo: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))


class Driver(DriverBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    reservation_id: Optional[int] = Field(default=None, foreign_key="reservation.id")