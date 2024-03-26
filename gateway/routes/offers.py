import datetime
import os
import uuid
from typing import List

from fastapi_jwt_auth import AuthJWT
from sqlalchemy import select, delete, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
import base64
import aiofiles
from models.offers import Offer, Appliance, AppliancesMap
from models.auth import User
from config.database import get_db

from schemas.offers import OfferSchema, OfferCreate, OfferEdit, OfferList, ApplianceSchema, Filters, Map

from config.main import get_address_data
from sqlalchemy.orm import selectinload

router = APIRouter(
    prefix="/v1/offer",
    tags=['Offer']
)


async def image_to_base64(image_path):
    async with aiofiles.open(image_path, "rb") as img_file:
        image_data = await img_file.read()
        base64_data = base64.b64encode(image_data)
        base64_string = base64_data.decode("utf-8")
        return base64_string


@router.post("/appliance", tags=['Appliance'], response_model=ApplianceSchema)
async def create_appliance(name: str, session: AsyncSession = Depends(get_db)):
    # Check if the appliance with the given name already exists
    existing_appliance = await session.execute(select(Appliance).where(Appliance.name == name))
    if existing_appliance.scalar():
        raise HTTPException(status_code=400, detail="Appliance with this name already exists")
    # Create a new appliance
    new_appliance = Appliance(name=name)
    session.add(new_appliance)
    await session.commit()
    return new_appliance


@router.delete("/appliance/{appliance_id}", tags=['Appliance'], response_model=ApplianceSchema)
async def delete_appliance(appliance_id: int, session: AsyncSession = Depends(get_db)):
    # Fetch the appliance to delete
    appliance = await session.get(Appliance, appliance_id)
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")

    # Delete the appliance from the database
    await session.delete(appliance)
    await session.commit()

    return appliance


@router.get("/appliances", tags=['Appliance'], response_model=List[ApplianceSchema])
async def get_all_appliances(session: AsyncSession = Depends(get_db)):
    appliances = await session.execute(select(Appliance))
    return appliances.scalars().all()


@router.post("/", tags=['Offer'], response_model=OfferSchema)
async def create_offer(data: OfferCreate, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    image_paths = []
    for idx, img_base64 in enumerate([data.img1, data.img2, data.img3]):
        if img_base64:
            img_data = base64.b64decode(img_base64.split(",")[1])
            ext = img_base64.split(",")[0].split("/")[-1].split(";")[0]
            filename = f"image_{uuid.uuid4().hex}.{ext}"
            image_path = os.path.join("images", filename)
            with open(image_path, "wb") as f:
                f.write(img_data)
            image_paths.append(image_path)
        else:
            image_paths.append(None)
    address_data = get_address_data(data.address)
    offer_data = data.dict()
    offer_data.update({
        "img1": image_paths[0],
        "img2": image_paths[1],
        "img3": image_paths[2]
    })
    offer_data.pop('appliances')
    offer = Offer(**offer_data, user_id=current_user, lat=address_data['lat'], lon=address_data['lon'],
                  country=address_data['country'])
    session.add(offer)
    await session.commit()
    for appliance in data.appliances:
        appliance_mapping = AppliancesMap(appliance_id=appliance, offer_id=offer.id)
        session.add(appliance_mapping)
    await session.commit()
    offer.appliances = [await session.get(Appliance, i[0].appliance_id) for i in
                        (await session.execute(select(AppliancesMap).where(AppliancesMap.offer_id == offer.id))).all()]
    offer.owner = await session.get(User, offer.user_id)
    if offer.img1:
        offer.img1 = await image_to_base64(offer.img1)
    if offer.img2:
        offer.img2 = await image_to_base64(offer.img2)
    if offer.img3:
        offer.img3 = await image_to_base64(offer.img3)
    return offer


@router.put("/{offer_id}", tags=['Offer'], response_model=OfferSchema)
def update_offer(offer_id: int, data: OfferEdit, Authorize: AuthJWT = Depends(),
                 session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()


@router.delete("/{offer_id}", tags=['Offer'], response_model=OfferSchema)
async def delete_offer(offer_id: int, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    offer = await session.get(Offer, offer_id)
    if offer.user_id != current_user:
        raise HTTPException(status_code=403)
    await session.delete(offer)
    await session.commit()
    return offer


@router.get("/one/{offer_id}", tags=['Offer'], response_model=OfferSchema)
async def offer(offer_id: int, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.appliances = [await session.get(Appliance, i[0].appliance_id) for i in
                        (await session.execute(select(AppliancesMap).where(AppliancesMap.offer_id == offer.id))).all()]
    offer.owner = await session.get(User, offer.user_id)
    if offer.img1:
        offer.img1 = await image_to_base64(offer.img1)
    if offer.img2:
        offer.img2 = await image_to_base64(offer.img2)
    if offer.img3:
        offer.img3 = await image_to_base64(offer.img3)
    return offer


@router.get("/all", tags=['Offer'], response_model=OfferList)
async def all_offers(filters: Filters, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    filter_conditions = []
    if filters.type:
        filter_conditions.append(Offer.type == filters.type)
    if filters.price_from is not None:
        filter_conditions.append(Offer.price >= filters.price_from)
    if filters.price_to is not None:
        filter_conditions.append(Offer.price <= filters.price_to)
    if filters.rooms:
        filter_conditions.append(Offer.rooms.in_(filters.rooms))
    if filters.area_from is not None:
        filter_conditions.append(Offer.area >= filters.area_from)
    if filters.area_to is not None:
        filter_conditions.append(Offer.area <= filters.area_to)
    if filters.floor_from is not None:
        filter_conditions.append(Offer.floor >= filters.floor_from)
    if filters.floor_to is not None:
        filter_conditions.append(Offer.floor <= filters.floor_to)
    if filters.appliance:
        for appliance in filters.appliance:
            filter_conditions.append(Appliance.id == appliance)
    if filters.renovation:
        filter_conditions.append(Offer.renovation.in_(filters.renovation))
    offers = (await session.execute(select(Offer).where(and_(*filter_conditions)))).all()
    offers_data = []
    for offer_row in offers:
        appliances = [
            await session.get(Appliance, i[0].appliance_id)
            for i in
            (await session.execute(select(AppliancesMap).where(AppliancesMap.offer_id == offer_row[0].id))).all()
        ]

        appliances_data = [{
            'id': appliance.id,
            'name': appliance.name
        } for appliance in appliances]

        owner = await session.get(User, offer_row[0].user_id)

        offer_schema_data = {
            "id": offer_row[0].id,
            "img1": offer_row[0].img1,
            "img2": offer_row[0].img2,
            "img3": offer_row[0].img3,
            "address": offer_row[0].address,
            "title": offer_row[0].title,
            "description": offer_row[0].description,
            "type": offer_row[0].type,
            "rooms": offer_row[0].rooms,
            "price": offer_row[0].price,
            "area": offer_row[0].area,
            "floor": offer_row[0].floor,
            "renovation": offer_row[0].renovation,
            "appliances": appliances_data,
            "owner": {
                'name': owner.name,
                'tg_username': owner.tg_username,
                'phone': owner.phone,
                'email': owner.email,
            }
        }
        if offer_schema_data['img1']:
            offer_schema_data['img1'] = await image_to_base64(offer_schema_data['img1'])
        if offer_schema_data['img2']:
            offer_schema_data['img2'] = await image_to_base64(offer_schema_data['img2'])
        if offer_schema_data['img3']:
            offer_schema_data['img3'] = await image_to_base64(offer_schema_data['img3'])

        offers_data.append(offer_schema_data)
    return {
        'offers': offers_data
    }


@router.get("/my", tags=['Offer'], response_model=OfferSchema)
async def my_offers(Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    current_user = Authorize.get_jwt_subject()
    offers = (await session.execute(select(Offer).where(Offer.user_id == current_user))).all()
    offers_data = []
    for offer_row in offers:
        appliances = [
            await session.get(Appliance, i[0].appliance_id)
            for i in
            (await session.execute(select(AppliancesMap).where(AppliancesMap.offer_id == offer_row[0].id))).all()
        ]

        appliances_data = [{
            'id': appliance.id,
            'name': appliance.name
        } for appliance in appliances]

        owner = await session.get(User, offer_row[0].user_id)

        offer_schema_data = {
            "id": offer_row[0].id,
            "img1": offer_row[0].img1,
            "img2": offer_row[0].img2,
            "img3": offer_row[0].img3,
            "address": offer_row[0].address,
            "title": offer_row[0].title,
            "description": offer_row[0].description,
            "type": offer_row[0].type,
            "rooms": offer_row[0].rooms,
            "price": offer_row[0].price,
            "area": offer_row[0].area,
            "floor": offer_row[0].floor,
            "renovation": offer_row[0].renovation,
            "appliances": appliances_data,
            "owner": {
                'name': owner.name,
                'tg_username': owner.tg_username,
                'phone': owner.phone,
                'email': owner.email,
            }
        }
        if offer_schema_data['img1']:
            offer_schema_data['img1'] = await image_to_base64(offer_schema_data['img1'])
        if offer_schema_data['img2']:
            offer_schema_data['img2'] = await image_to_base64(offer_schema_data['img2'])
        if offer_schema_data['img3']:
            offer_schema_data['img3'] = await image_to_base64(offer_schema_data['img3'])

        offers_data.append(offer_schema_data)
    return {
        'offers': offers_data
    }


@router.get("/map", tags=['Offer'], response_model=OfferSchema)
async def my_offers(map: Map, filters: Filters, Authorize: AuthJWT = Depends(), session: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    filter_conditions = []
    if filters.type:
        filter_conditions.append(Offer.type == filters.type)
    if filters.price_from is not None:
        filter_conditions.append(Offer.price >= filters.price_from)
    if filters.price_to is not None:
        filter_conditions.append(Offer.price <= filters.price_to)
    if filters.rooms:
        filter_conditions.append(Offer.rooms.in_(filters.rooms))
    if filters.area_from is not None:
        filter_conditions.append(Offer.area >= filters.area_from)
    if filters.area_to is not None:
        filter_conditions.append(Offer.area <= filters.area_to)
    if filters.floor_from is not None:
        filter_conditions.append(Offer.floor >= filters.floor_from)
    if filters.floor_to is not None:
        filter_conditions.append(Offer.floor <= filters.floor_to)
    if filters.appliance:
        for appliance in filters.appliance:
            filter_conditions.append(Appliance.id == appliance)
    if filters.renovation:
        filter_conditions.append(Offer.renovation.in_(filters.renovation))
    offers = (await session.execute(select(Offer).where(and_(*filter_conditions)))).all()
    offers_data = []
    for offer_row in offers:
        appliances = [
            await session.get(Appliance, i[0].appliance_id)
            for i in
            (await session.execute(select(AppliancesMap).where(AppliancesMap.offer_id == offer_row[0].id))).all()
        ]

        appliances_data = [{
            'id': appliance.id,
            'name': appliance.name
        } for appliance in appliances]

        owner = await session.get(User, offer_row[0].user_id)

        offer_schema_data = {
            "id": offer_row[0].id,
            "img1": offer_row[0].img1,
            "img2": offer_row[0].img2,
            "img3": offer_row[0].img3,
            "address": offer_row[0].address,
            "title": offer_row[0].title,
            "description": offer_row[0].description,
            "type": offer_row[0].type,
            "rooms": offer_row[0].rooms,
            "price": offer_row[0].price,
            "area": offer_row[0].area,
            "floor": offer_row[0].floor,
            "renovation": offer_row[0].renovation,
            "appliances": appliances_data,
            "owner": {
                'name': owner.name,
                'tg_username': owner.tg_username,
                'phone': owner.phone,
                'email': owner.email,
            }
        }
        if offer_schema_data['img1']:
            offer_schema_data['img1'] = await image_to_base64(offer_schema_data['img1'])
        if offer_schema_data['img2']:
            offer_schema_data['img2'] = await image_to_base64(offer_schema_data['img2'])
        if offer_schema_data['img3']:
            offer_schema_data['img3'] = await image_to_base64(offer_schema_data['img3'])

        offers_data.append(offer_schema_data)
    return {
        'offers': offers_data
    }
