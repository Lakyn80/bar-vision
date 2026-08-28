from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.bottles.router import router as bottles_router
from app.modules.products.router import router as products_router
from app.modules.system.router import router as system_router
from app.modules.venues.router import router as venues_router


api_router = APIRouter()

api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(venues_router)
api_router.include_router(products_router)
api_router.include_router(bottles_router)
