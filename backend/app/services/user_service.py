from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AuthError, ConflictError
from app.core.security import hash_password, verify_password
from app.core.utils import to_object_id, utcnow
from app.database.indexes import USERS
from app.database.mongodb import get_db
from app.schemas.user import UserCreate, UserOut


def to_user_out(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        email=doc["email"],
        full_name=doc["full_name"],
        created_at=doc["created_at"],
    )


async def create_user(data: UserCreate) -> dict:
    doc = {
        "email": data.email.lower(),
        "full_name": data.full_name.strip(),
        "password_hash": hash_password(data.password),
        "created_at": utcnow(),
    }
    try:
        result = await get_db()[USERS].insert_one(doc)
    except DuplicateKeyError:
        raise ConflictError("An account with this email already exists")
    doc["_id"] = result.inserted_id
    return doc


async def authenticate(email: str, password: str) -> dict:
    user = await get_db()[USERS].find_one({"email": email.lower()})
    if not user or not verify_password(password, user["password_hash"]):
        raise AuthError("Incorrect email or password")
    return user


async def get_user_by_id(user_id: str) -> dict | None:
    oid = to_object_id(user_id)
    if oid is None:
        return None
    return await get_db()[USERS].find_one({"_id": oid})
