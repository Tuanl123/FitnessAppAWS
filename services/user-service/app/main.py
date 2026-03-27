"""User Service — FastAPI application entry point.

Handles user registration, authentication, and profile management.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.middleware import CorrelationIdMiddleware
from app.routers import auth, users
from shared.auth import configure as configure_auth

configure_auth(settings.jwt_secret, settings.jwt_algorithm)

logger = logging.getLogger("user-service")

app = FastAPI(
    title="Fitness Tracker — User Service",
    version="0.1.0",
    root_path="/api/users",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(users.router, tags=["profile"])

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-service"}
