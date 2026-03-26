"""User Service configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    user_db_url: str = "postgresql+asyncpg://postgres:devpass@localhost:5432/user_db"
    jwt_secret: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    environment: str = "local"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
