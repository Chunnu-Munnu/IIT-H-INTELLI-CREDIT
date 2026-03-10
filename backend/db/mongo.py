from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
from app.config import settings

_client: AsyncIOMotorClient = None
_db = None


async def connect_to_mongo():
    global _client, _db
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    _db = _client[settings.DB_NAME]
    logger.info(f"Connected to MongoDB: {settings.DB_NAME}")


async def close_mongo_connection():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


from datetime import datetime, date


def jsonify_mongo(data):
    """
    Recursively convert date objects to datetime objects for MongoDB.
    Also handles Pydantic models by calling model_dump().
    """
    if hasattr(data, "model_dump"):
        data = data.model_dump()
    elif hasattr(data, "dict"): # For older Pydantic or other objects
        data = data.dict()

    if isinstance(data, dict):
        return {k: jsonify_mongo(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [jsonify_mongo(i) for i in data]
    elif isinstance(data, date) and not isinstance(data, datetime):
        return datetime(data.year, data.month, data.day)
    return data


def get_database():
    return _db
