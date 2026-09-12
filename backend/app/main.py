import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config import get_settings
from app.core.limiter import limiter
from app.database import Base, engine
from app.logging_config import configure_logging
from app.routers import admin, api, postback
from app.routers.bot import bot_router

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.is_production:
        # In production, use Alembic migrations (see backend/migrations) instead
        # of create_all so schema changes are reviewable and reversible.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created / verified (dev mode)")
    else:
        logger.info("Production mode: skipping create_all, run `alembic upgrade head` before starting")
    yield
    await engine.dispose()


app = FastAPI(title="Telegram Earn Bot API", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if not settings.cors_origins:
    logger.warning("CORS_ORIGINS is empty — no browser origin will be allowed to call this API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Signature"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(api.router)
app.include_router(admin.router)
app.include_router(postback.router)
app.include_router(bot_router, prefix="/bot")


@app.get("/")
async def root():
    return {"status": "ok", "service": "earn-bot-api", "version": app.version}


@app.get("/health")
async def health():
    return {"status": "healthy"}
