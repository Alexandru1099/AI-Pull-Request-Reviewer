from fastapi import APIRouter

from .analyze import router as analyze_router
from .auth import router as auth_router
from .diff import router as diff_router
from .evaluation import router as evaluation_router
from .health import router as health_router
from .review import router as review_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(review_router, tags=["review"])
api_router.include_router(diff_router, tags=["diff"])
api_router.include_router(analyze_router, tags=["analyze"])
api_router.include_router(evaluation_router, tags=["evaluation"])
