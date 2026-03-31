"""Metrics Service configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    sqs_endpoint_url: str | None = "http://localhost:4566"
    sqs_queue_name: str = "analytics-queue"
    analytics_db_url: str = "postgresql://postgres:devpass@localhost:5432/analytics_db"
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:5173"]
    aws_region: str = "us-east-1"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
