from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import sys
import time
import traceback
import os

from app.config import settings
from db.mongo import connect_to_mongo, close_mongo_connection
from db.indexes import create_indexes
from api.routes.auth_routes import router as auth_router
from api.routes.ingestion_routes import router as ingestion_router
from api.routes.results_routes import router as results_router
from api.routes.analysis_routes import router as analysis_router
from api.routes.recommendation_routes import router as recommendation_router
from api.routes.qualitative_routes import router as qualitative_router

# ──────────────────────────────────────────────
# LOGURU — verbose console output (DEBUG level)
# ──────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    colorize=True,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
)
logger.add(
    "./logs/intelli_credit_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
)

logger.info("=" * 60)
logger.info("  INTELLI-CREDIT ENGINE — VERBOSE MODE")
logger.info("=" * 60)

# Global model store
_model_store = None
_loaded_models = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model_store, _loaded_models
    logger.info("Starting Intelli-Credit AI Engine...")
    await connect_to_mongo()
    await create_indexes()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
    os.makedirs("./data/models", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    logger.info(f"Upload dir : {os.path.abspath(settings.UPLOAD_DIR)}")
    logger.info(f"Processed  : {os.path.abspath(settings.PROCESSED_DIR)}")
    try:
        from analysis.ensemble.model_store import ModelStore
        _model_store = ModelStore()
        _loaded_models = _model_store.load_latest()
        if _loaded_models:
            logger.success("✓ ML models pre-loaded at startup")
        else:
            logger.warning("No trained models found — run ml_training/run_training.py")
    except Exception as e:
        logger.warning(f"Model pre-load failed: {e}")
    logger.success("Intelli-Credit ready — http://localhost:8000")
    logger.success("Swagger UI     — http://localhost:8000/docs")
    yield
    await close_mongo_connection()
    logger.info("Intelli-Credit shutdown complete.")


app = FastAPI(
    title="Intelli-Credit AI Engine",
    description="AI-powered Corporate Credit Appraisal Engine for Indian Corporate Lending",
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# REQUEST / RESPONSE LOGGING MIDDLEWARE
# ──────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    logger.debug(f"→ {request.method:6} {request.url.path}")
    try:
        response = await call_next(request)
        ms = (time.time() - start) * 1000
        if response.status_code < 400:
            logger.success(f"← {request.method:6} {request.url.path} [{response.status_code}] {ms:.0f}ms")
        else:
            logger.error(f"← {request.method:6} {request.url.path} [{response.status_code}] {ms:.0f}ms")
        return response
    except Exception as exc:
        ms = (time.time() - start) * 1000
        logger.error(
            f"✗ UNHANDLED {request.method} {request.url.path} after {ms:.0f}ms\n"
            + traceback.format_exc()
        )
        return JSONResponse(status_code=500, content={"detail": str(exc)})


# CORS — allow all Vite dev ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router,           prefix="/auth",  tags=["auth"])
app.include_router(ingestion_router,      prefix="/cases", tags=["cases"])
app.include_router(results_router,        prefix="/cases", tags=["results"])
app.include_router(analysis_router,       prefix="/cases", tags=["analysis"])
app.include_router(recommendation_router, prefix="/cases", tags=["recommendation"])
app.include_router(qualitative_router,  prefix="/cases", tags=["qualitative"])

# Static files for processed docs
try:
    app.mount("/processed", StaticFiles(directory="./data/processed"), name="processed")
except Exception:
    pass


@app.get("/health")
async def health_check():
    global _loaded_models
    model_status = "loaded" if _loaded_models else "not_loaded"
    return {"status": "healthy", "service": "Intelli-Credit", "ml_model": model_status}


@app.post("/internal/reload-models")
async def reload_models():
    global _model_store, _loaded_models
    try:
        from analysis.ensemble.model_store import ModelStore
        _model_store = ModelStore()
        _loaded_models = _model_store.load_latest()
        if _loaded_models:
            return {"status": "reloaded", "message": "Models reloaded successfully"}
        return {"status": "no_models", "message": "No trained models found"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/ml/model-info")
async def model_info():
    global _model_store
    if _model_store and _model_store._metadata:
        return _model_store._metadata
    return {"status": "no_model_loaded", "message": "Run ml_training/run_training.py to train"}
