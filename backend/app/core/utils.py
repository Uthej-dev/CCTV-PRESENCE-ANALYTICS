from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_object_id(value: str) -> ObjectId | None:
    """Parse a string into an ObjectId, returning None if it is not valid."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
