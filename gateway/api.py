import datetime
import random
import string
from typing import List

from redis import asyncio as aioredis
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi_pagination import add_pagination
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import or_, and_
from fastapi.responses import HTMLResponse, JSONResponse
from config.database import get_db, init_db
from config.main import Settings, send_email, send_tg
from models.auth import User
from routes.offers import router as offers_router
from schemas.auth import SignUp, NewPassword, SignIn, EditData, SimpleResponse, TokenResponse, ProfileResponse, \
    Authorise, ResetPassword

app = FastAPI(
    title="Realty Agency",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://31.129.44.104:5001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization"],
)

add_pagination(app)

app.include_router(offers_router)


@AuthJWT.load_config
def get_config():
    return Settings()


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


def clean_phone(phone):
    return phone.replace('(', '').replace(')', '').replace('-', '').replace('+', '').replace(' ', '')


def generate_password(length=6):
    characters = string.ascii_letters + string.digits + '#$%&@?'
    password = ''.join(random.choice(characters) for i in range(length))
    return password


async def authenticate_user(username: str, password: str, session: AsyncSession):
    result = await session.execute(
        select(User).where(
            (User.tg_username == username) |
            (User.phone == clean_phone(username))
        )
    )
    user = result.first()
    if user and user[0].verify_password(password):
        return user[0]
    return None


async def auth_user(tg_id: str, session: AsyncSession):
    result = await session.execute(
        select(User).where(
            (User.tg_id == tg_id)
        )
    )
    user = result.first()
    global redis_pool
    if user:
        return user[0]
    return None


async def register_user(user_data: SignUp, session: AsyncSession):
    filter_args = [
        (User.tg_id == user_data.tg_id)
    ]

    query = select(User).where(or_(*filter_args))
    result = await session.execute(query)
    user = result.first()
    if user:
        return None
    user = User(
        role=user_data.role,
        name=user_data.name,
        tg_id=user_data.tg_id,
        tg_username=user_data.tg_username

    )
    session.add(user)
    await session.commit()
    return user


@app.on_event("startup")
async def startup_event():
    await init_db()
    global redis_pool
    redis = aioredis.from_url("redis://127.0.0.1:6379",
                              encoding="utf8", decode_responses=True)
    redis_pool = redis
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


@app.on_event("shutdown")
async def shutdown_event():
    global redis_pool
    await redis_pool.close()


@app.get("/v1/send-otp", tags=['Account'], response_model=SimpleResponse)
async def send_otp(tg_id: str, session: AsyncSession = Depends(get_db)):
    user = await session.execute(
        select(User).where((User.tg_id == tg_id))
    )
    user = user.first()
    global redis_pool
    if user:
        otp = random.randint(10000, 99999)
        await redis_pool.set(f"otp:{tg_id}", otp, ex=600)
        msg_body = f'''Ваш код подтверждения: {otp}'''
        try:
            send_tg(tg_id, msg_body)
            return {'result': True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {'result': False}


@app.post("/v1/auth", tags=['Account'], response_model=TokenResponse)
async def auth(data: Authorise, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    user = await auth_user(data.tg_id, session)
    if user is None:
        raise HTTPException(
            status_code=401, detail="Incorrect code")
    access_token = Authorize.create_access_token(subject=user.id)
    refresh_token = Authorize.create_refresh_token(subject=user.id)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'customer_id': user.id
    }


@app.post("/v1/signin", tags=['Account'], response_model=TokenResponse)
async def signin(data: SignIn, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    user = await authenticate_user(data.username, data.password, session)
    if user is None:
        raise HTTPException(
            status_code=401, detail="Incorrect username or password")
    access_token = Authorize.create_access_token(subject=user.id)
    refresh_token = Authorize.create_refresh_token(subject=user.id)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'customer_id': user.id
    }


@app.post('/v1/refresh-token', tags=['Account'], response_model=TokenResponse)
async def refresh(Authorize: AuthJWT = Depends()):
    Authorize.jwt_refresh_token_required()
    current_user = Authorize.get_jwt_subject()
    access_token = Authorize.create_access_token(subject=current_user)
    refresh_token = Authorize.create_refresh_token(subject=current_user)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'customer_id': user.id
    }


@app.post('/v1/signup', tags=['Account'], response_model=SimpleResponse)
async def signup(data: SignUp, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    user = await register_user(data, session)
    if user is None:
        raise HTTPException(status_code=403, detail="user_not_allowed")
    return {
        'result': True
    }


@app.get('/v1/profile', tags=['Account'], response_model=ProfileResponse)
async def profile(Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    user = await session.execute(
        select(User).where((User.id == current_user))
    )
    user = user.fetchone()
    if user:
        return {'profile': {
            'id': user[0].id,
            'role': user[0].role,
            'phone': user[0].phone,
            'username': user[0].tg_username,
            'tg_id': user[0].tg_id,
            'name': user[0].name,
            'email': user[0].email,
            'status': user[0].status,
        }}
    raise HTTPException(status_code=404, detail='user_not_found')


@app.put('/v1/edit-data', tags=['Account'], response_model=ProfileResponse)
async def edit_data(data: EditData, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    user = await session.execute(
        select(User).where((User.id == current_user))
    )
    user = user.fetchone()
    if user:
        user[0].name = data.name
        user[0].email = data.email
        user[0].phone = data.phone
        user[0].tg_username = data.username
        await session.commit()
        return {'profile': {
            'id': user[0].id,
            'role': user[0].role,
            'phone': user[0].phone,
            'username': user[0].tg_username,
            'tg_id': user[0].tg_id,
            'name': user[0].name,
            'email': user[0].email,
            'status': user[0].status,
        }}
    raise HTTPException(status_code=404, detail='user_not_found')


@app.put('/v1/set-password', tags=['Account'], response_model=SimpleResponse)
async def set_password(data: NewPassword, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    if data.confirm_password == data.new_password:
        user = await session.execute(
            select(User).where((User.id == current_user))
        )
        user = user.fetchone()
        if user:
            user[0].get_password_hash(data.new_password)
            await session.commit()
            return {'result': True}
        raise HTTPException(status_code=404, detail='user_not_found')
    raise HTTPException(status_code=400, detail='different_values')


@app.get("/v1/send-reset-otp", tags=['Account'], response_model=SimpleResponse)
async def send_reset_otp(username: str, session: AsyncSession = Depends(get_db)):
    user = await session.execute(
        select(User).where((User.tg_username == username))
    )
    user = user.first()
    global redis_pool
    if user:
        otp = random.randint(10000, 99999)
        await redis_pool.set(f"otp:{username}", otp, ex=600)
        msg_body = f'''Ваш код подтверждения: {otp}'''
        try:
            send_tg(user[0].tg_id, msg_body)
            return {'result': True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {'result': False}


@app.post("/v1/reset-password", tags=['Account'], response_model=SimpleResponse)
async def reset_password(data: ResetPassword, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(User).where(
            (User.tg_username == data.username)
        )
    )
    user = result.first()
    global redis_pool
    if user and str(data.code) == str(await redis_pool.get(f'otp:{data.username}')):
        if data.new_password == data.confirm_password:
            user[0].get_password_hash(data.new_password)
            await session.commit()
            return {'result': True}
        raise HTTPException(status_code=400, detail='different_values')
    raise HTTPException(status_code=404, detail='user_not_found')
