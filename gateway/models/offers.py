from datetime import datetime

from sqlalchemy import Boolean, Enum, Text, DateTime
from sqlalchemy import Table, Column, Integer, String, ForeignKey, REAL
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

from config.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Offer(Base):
    __tablename__ = "offer"
    id: int = Column(Integer, primary_key=True)
    photo: str = Column(String(128), nullable=True)
    user_id: int = Column(ForeignKey('customer.id'), nullable=False)
    img1: str = Column(String, nullable=False)
    img2: str = Column(String, nullable=True)
    img3: str = Column(String, nullable=True)
    address: str = Column(String(512), nullable=False)
    country: str = Column(String(64), nullable=True)
    lon: float = Column(REAL, nullable=True)
    lat: float = Column(REAL, nullable=True)
    title: str = Column(String(512), nullable=False)
    description: str = Column(String(2048), nullable=False)
    type: str = Column(String(16), nullable=False)
    rooms: str = Column(String(8), nullable=False)
    price: float = Column(REAL, nullable=False)
    area: float = Column(REAL, nullable=False)
    floor: int = Column(Integer, nullable=False)
    renovation: str = Column(String(64), nullable=False)

    appliances = relationship("Appliance", secondary="appliances_map")


class Appliance(Base):
    __tablename__ = "appliance"
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(128), nullable=False)


class AppliancesMap(Base):
    __tablename__ = "appliances_map"
    id: int = Column(Integer, primary_key=True)
    appliance_id: int = Column(ForeignKey('appliance.id'), nullable=False)
    offer_id: int = Column(ForeignKey('offer.id'), nullable=False)

