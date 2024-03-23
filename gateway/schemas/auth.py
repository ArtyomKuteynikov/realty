import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Roles(str, Enum):
    admin = 'admin'
    partner = 'client'


class Authorise(BaseModel):
    tg_id: str
    code: int


class SignIn(BaseModel):
    username: str
    password: str


class SignUp(BaseModel):
    role: Roles
    name: str
    tg_id: str
    tg_username: str


class SendCode(BaseModel):
    tg_id: str


class TgOTP(BaseModel):
    tg_id: str
    code: int


class NewPassword(BaseModel):
    new_password: str
    confirm_password: str


class ResetPassword(BaseModel):
    username: str
    code: int
    new_password: str
    confirm_password: str


class EditData(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    username: str


class SimpleResponse(BaseModel):
    result: bool


class TokenResponse(BaseModel):
    access_token: str
    customer_id: int


class Profile(BaseModel):
    id: int
    role: Roles
    phone: Optional[str] = None
    username: str
    tg_id: str
    name: str
    email: Optional[str] = None
    status: int


class ProfileResponse(BaseModel):
    profile: Profile
