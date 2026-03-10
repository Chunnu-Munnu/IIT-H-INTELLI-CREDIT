from fastapi import APIRouter, HTTPException, Response, Depends
from auth.models import UserCreate, UserLogin, UserResponse, TokenResponse
from auth.service import verify_password, create_access_token, get_current_user
from auth.mongo import create_user, get_user_by_email, get_user_by_id
from datetime import datetime

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, response: Response):
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user_id = await create_user(user_data)
    token = create_access_token({"sub": user_id})
    user = await get_user_by_id(user_id)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user["email"],
            name=user["name"],
            organization=user["organization"],
            created_at=user["created_at"],
            case_count=user.get("case_count", 0),
        )
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, response: Response):
    user = await get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id})
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user_id,
            email=user["email"],
            name=user["name"],
            organization=user["organization"],
            created_at=user["created_at"],
            case_count=user.get("case_count", 0),
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}
