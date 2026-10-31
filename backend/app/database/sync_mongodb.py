"""Synchronous MongoDB client for camera worker threads.

The API uses the async client (event loop); workers run in plain threads, so
they use PyMongo's thread-safe synchronous client instead.
"""
import threading

from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

_client: MongoClient | None = None
_lock = threading.Lock()


def get_sync_db() -> Database:
    global _client
    with _lock:
        if _client is None:
            _client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000, tz_aware=True)
    return _client[settings.MONGODB_DB]


def close_sync_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None
