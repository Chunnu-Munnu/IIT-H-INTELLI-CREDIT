from fastapi import HTTPException
from bson import ObjectId
from datetime import datetime
from loguru import logger

from db.mongo import get_database
from auth.models import UserCreate
from auth.service import hash_password


async def create_user(user: UserCreate) -> str:
    db = get_database()
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    doc = {
        "email": user.email,
        "name": user.name,
        "organization": user.organization,
        "hashed_password": hash_password(user.password),
        "role": "credit_officer",
        "created_at": datetime.utcnow(),
        "case_count": 0,
    }
    result = await db.users.insert_one(doc)
    return str(result.inserted_id)


async def get_user_by_email(email: str) -> dict | None:
    db = get_database()
    return await db.users.find_one({"email": email})


async def get_user_by_id(user_id: str) -> dict | None:
    db = get_database()
    try:
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


async def increment_case_count(user_id: str) -> None:
    db = get_database()
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"case_count": 1}},
    )
