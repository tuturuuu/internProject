from fastapi import APIRouter

from app.api.routes.search import router as search_router
from app.api.routes.frontend import router as frontend_router


router = APIRouter(prefix="/api")
router.include_router(search_router)
router.include_router(frontend_router)
