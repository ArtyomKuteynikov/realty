import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Types(str, Enum):
    apartment = 'Apartment'
    room = 'Room'
    house = 'House'


class Rooms(str, Enum):
    studio = 'Studio'
    free = 'Free planing'
    one = '1'
    two = '2'
    three = '3'
    four = '4'
    five = '5'
    more = '6+'


class Renovation(str, Enum):
    any = 'Any'
    without = 'Without renovation'
    cosmetic = 'Cosmetic renovation'
    euro = 'Euro renovation'
    designer = 'Designer renovation'


class ApplianceSchema(BaseModel):
    id: int
    name: str


class Owner(BaseModel):
    name: str
    tg_username: str
    photo: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class OfferCreate(BaseModel):
    img1: str
    img2: Optional[str] = None
    img3: Optional[str] = None
    address: str
    title: str
    description: str
    type: Types
    rooms: Rooms
    price: float
    area: float
    floor: int
    renovation: Renovation
    appliances: List[int]


class OfferEdit(BaseModel):
    img1: Optional[str] = None
    img2: Optional[str] = None
    img3: Optional[str] = None
    address: str
    title: str
    description: str
    type: Types
    rooms: Rooms
    price: float
    area: float
    floor: int
    renovation: Renovation
    appliances: List[int]


class OfferSchema(BaseModel):
    id: int
    img1: str
    img2: Optional[str] = None
    img3: Optional[str] = None
    address: str
    country: Optional[str] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    title: str
    description: str
    type: Types
    rooms: Rooms
    price: float
    area: float
    floor: int
    renovation: Renovation
    appliances: List[ApplianceSchema]
    owner: Owner


class OfferList(BaseModel):
    offers: List[OfferSchema]


class Filters(BaseModel):
    type: Optional[Types] = None
    price_from: Optional[float] = None
    price_to: Optional[float] = None
    rooms: List[Rooms]
    area_from: Optional[float] = None
    area_to: Optional[float] = None
    floor_from: Optional[float] = None
    floor_to: Optional[float] = None
    appliance: List[int]
    renovation: List[Renovation]


class Coordinates(BaseModel):
    lon: float
    lat: float


class Map(BaseModel):
    coordinates_min: Coordinates
    coordinates_max: Coordinates
