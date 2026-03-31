"""Metrics Service — FastAPI application entry point.

Handles metric ingestion (writes to SQS) and metric/analytics retrieval
(reads from analytics_db).
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.middleware import CorrelationIdMiddleware
from app.routers import ingest, read
from shared.auth import configure as configure_auth

configure_auth(settings.jwt_secret, settings.jwt_algorithm)

logger = logging.getLogger("metrics-service")

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="Fitness Tracker — Metrics Service",
    version="0.1.0",
    root_path="/api/metrics",
)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded. {exc.detail}"},
    )


app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, tags=["ingest"])
app.include_router(read.router, tags=["read"])

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "metrics-service"}
