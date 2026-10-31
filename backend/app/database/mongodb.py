"""MongoDB connection management.

Uses PyMongo's native async client (AsyncMongoClient) for the API layer.
The CV workers (added in later stages) run in background threads and will use
a regular synchronous MongoClient pointing at the same database.
"""
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings
from app.database.indexes import create_indexes

_client: AsyncMongoClient | None = None


async def connect_to_mongo() -> None:
    global _client
    # tz_aware=True -> datetimes come back as timezone-aware UTC
    _client = AsyncMongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000, tz_aware=True)
    # Fail fast on startup if MongoDB is unreachable
    await _client.admin.command("ping")
    await create_indexes(_client[settings.MONGODB_DB])


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


def get_db() -> AsyncDatabase:
    if _client is None:
        raise RuntimeError("MongoDB client is not initialised")
    return _client[settings.MONGODB_DB]


async def ping_db() -> bool:
    try:
        await get_db().command("ping")
        return True
    except Exception:
        return False
