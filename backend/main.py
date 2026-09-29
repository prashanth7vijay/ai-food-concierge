from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import chat, compare, conversations, food, preferences, saved_items
from backend.core.config import get_settings
from backend.core.logging import (
    configure_logging,
    get_logger,
    log_event,
    request_id_var,
)
from backend.database.session import Base, engine

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For local/dev/test convenience only. Production schema changes go
    # through Alembic migrations (backend/alembic) — this create_all is a
    # no-op against a DB that already has the migrated schema in place
    # (it only creates tables that don't exist yet).
    if settings.ENVIRONMENT != "production":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        latency_ms = (time.perf_counter() - start) * 1000
        log_event(
            logger,
            logging.INFO,
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            latency_ms=round(latency_ms, 2),
        )
        request_id_var.reset(token)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log_event(logger, logging.ERROR, "unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}


app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(conversations.router, prefix=settings.API_PREFIX)
app.include_router(preferences.router, prefix=settings.API_PREFIX)
app.include_router(food.router, prefix=settings.API_PREFIX)
app.include_router(compare.router, prefix=settings.API_PREFIX)
app.include_router(saved_items.router, prefix=settings.API_PREFIX)
