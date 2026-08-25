"""Framework-only health/root endpoint."""
from fastapi import APIRouter


def build_root_router() -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def root() -> dict[str, str]:
        return {"message": "IHCA API"}

    return router
