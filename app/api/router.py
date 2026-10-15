from fastapi import APIRouter

from app.api.routers import auth, images, jobs, metrics, outputs, system, videos

router = APIRouter()
router.include_router(auth.router)
router.include_router(metrics.router)
router.include_router(system.router)
router.include_router(jobs.router)
router.include_router(images.router)
router.include_router(videos.router)
router.include_router(outputs.router)
