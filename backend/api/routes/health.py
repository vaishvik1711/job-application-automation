"""Health check endpoint."""
from fastapi import APIRouter
from api.schemas import ApiResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse)
async def health_check():
    return ApiResponse[HealthResponse](
        data=HealthResponse(status="ok", version="1.0.0"),
    )