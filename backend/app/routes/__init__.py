from fastapi import APIRouter

from app.routes.tasks import router as tasks_router
from app.routes.wallet import router as wallet_router
from app.routes.deposits import router as deposits_router
from app.routes.adsgram import router as adsgram_router

router = APIRouter()

router.include_router(tasks_router)
router.include_router(wallet_router)
router.include_router(deposits_router)
router.include_router(adsgram_router)
