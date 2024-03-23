from datetime import datetime

from sqlalchemy import Boolean, Enum, Text, DateTime
from sqlalchemy import Table, Column, Integer, String, ForeignKey, REAL
from sqlalchemy.orm import relationship
from passlib.context import CryptContext

from config.database import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "customer"
    id: int = Column(Integer, primary_key=True)
    role: str = Column(String(50), nullable=False)
    name: str = Column(String(50), nullable=False)
    tg_id: str = Column(String(50), nullable=False)
    tg_username: str = Column(String(50), nullable=False)
    phone: str = Column(String(50), nullable=True)
    email: str = Column(String(50), nullable=True)
    password: str = Column(String(256), nullable=True)
    status: int = Column(Integer, default=0)

    def get_password_hash(self, password):
        self.password = pwd_context.hash(password)
        return pwd_context.hash(password)

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password)
