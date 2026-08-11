"""Matching API routes for weights and threshold configuration."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.schemas import MatchWeightsSchema, ThresholdSchema, ApiResponse
from api.dependencies import get_db_session
from database.models import MatchingConfig

router = APIRouter()


@router.get("/matching/weights", response_model=ApiResponse)
async def get_weights(session: AsyncSession = Depends(get_db_session)):
    """Get matching weights configuration."""
    result = await session.execute(select(MatchingConfig))
    config = result.scalars().first()

    if not config:
        # Return defaults
        return ApiResponse(data={
            "skills": 30,
            "experience": 25,
            "education": 10,
            "location": 15,
            "keywords": 20,
        })

    weights = config.default_weights
    return ApiResponse(data=weights)


@router.patch("/matching/weights", response_model=ApiResponse)
async def update_weights(
    weights: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update matching weights."""
    result = await session.execute(select(MatchingConfig))
    config = result.scalars().first()

    if not config:
        config = MatchingConfig(default_weights=weights)
        session.add(config)
    else:
        config.default_weights = weights

    await session.flush()

    return ApiResponse(data=weights)


@router.get("/matching/threshold", response_model=ApiResponse)
async def get_threshold(session: AsyncSession = Depends(get_db_session)):
    """Get the auto-qualify threshold."""
    result = await session.execute(select(MatchingConfig))
    config = result.scalars().first()

    if not config:
        return ApiResponse(data={"threshold": 75})

    return ApiResponse(data={"threshold": int(config.auto_qualify_threshold)})


@router.patch("/matching/threshold", response_model=ApiResponse)
async def update_threshold(
    data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update the auto-qualify threshold."""
    threshold = data.get("threshold", 75)

    result = await session.execute(select(MatchingConfig))
    config = result.scalars().first()

    if not config:
        config = MatchingConfig(auto_qualify_threshold=float(threshold))
        session.add(config)
    else:
        config.auto_qualify_threshold = float(threshold)

    await session.flush()

    return ApiResponse(data={"threshold": int(threshold)})