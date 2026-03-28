"""User profile CRUD routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ProfileResponse, ProfileUpdateRequest
from app.models import User
from shared.auth import get_current_user

router = APIRouter()


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        age=user.age,
        weight=user.weight,
        fitness_goals=user.fitness_goals,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the authenticated user's profile fields (partial update)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        age=user.age,
        weight=user.weight,
        fitness_goals=user.fitness_goals,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
