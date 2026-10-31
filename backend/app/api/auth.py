from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserOut
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user["_id"])),
        user=user_service.to_user_out(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate):
    user = await user_service.create_user(data)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    user = await user_service.authenticate(data.email, data.password)
    return _token_response(user)


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return user_service.to_user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: dict = Depends(get_current_user)):
    # JWTs are stateless: the client deletes its token. This endpoint exists so the
    # frontend has a single logout call (and a place to add token revocation later).
    return None
