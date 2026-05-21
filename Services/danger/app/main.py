"""
CompanionIO – Danger Detection Service
FastAPI application entry point
"""
import time
import uuid
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.routes import router
from app.core.config import settings
from app.core.model_registry import ModelRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("danger_detection")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup, release on shutdown."""
    logger.info("🔴 Danger Detection Service starting – loading models…")
    registry = ModelRegistry.get_instance()
    await registry.load_all()
    logger.info("✅ All models loaded – service ready.")
    yield
    logger.info("🛑 Shutting down – releasing model resources.")
    await registry.unload_all()


app = FastAPI(
    title="CompanionIO – Danger Detection Service",
    version="1.0.0",
    description=(
        "Detects dangerous situations from audio via sound classification, "
        "emotion detection, and text analysis."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.1f}"
    return response


app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    registry = ModelRegistry.get_instance()
    return {
        "status": "ok",
        "models_loaded": registry.all_loaded(),
        "service": "danger-detection",
        "version": "1.0.0",
    }
