from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.services.user_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Resolve the logged-in user from the `Authorization: Bearer <token>` header."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    return await _user_from_token(credentials.credentials, unauthorized)


async def get_current_user_from_query(token: str = Query(..., description="JWT access token")) -> dict:
    """For endpoints loaded by <img>/<video> tags, which cannot send an Authorization header."""
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return await _user_from_token(token, unauthorized)


async def _user_from_token(token: str, unauthorized: HTTPException) -> dict:
    user_id = decode_access_token(token)
    if user_id is None:
        raise unauthorized
    user = await get_user_by_id(user_id)
    if user is None:
        raise unauthorized
    return user
