from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.auth import get_current_user
from app.core.errors import api_error
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    existing = await db.execute(select(User.id).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise api_error(409, "email_already_registered", "An account with this email already exists")

    user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=await run_in_threadpool(hash_password, request.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint_name != "ix_users_email" and "UNIQUE constraint failed: users.email" not in str(exc.orig):
            raise
        raise api_error(
            409,
            "email_already_registered",
            "An account with this email already exists",
        )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    valid_password = False
    if user is not None:
        valid_password = await run_in_threadpool(
            verify_password,
            request.password,
            user.hashed_password,
        )

    if user is None or not valid_password or not user.is_active:
        raise api_error(401, "invalid_credentials", "Email or password is incorrect")

    token = create_access_token({"sub": str(user.id), "token_type": "access"})
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserRead, summary="Get the current user")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user
