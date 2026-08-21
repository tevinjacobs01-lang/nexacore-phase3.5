"""
Application configuration, loaded from environment variables (.env).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    # General
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "NexaCore Property Intelligence"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://nexacore:nexacore@localhost:5432/nexacore"

    # Auth
    JWT_SECRET_KEY: str = "change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177"
    ]

    # Rate limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # AI Assistant
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # Upload safety
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024


settings = Settings()