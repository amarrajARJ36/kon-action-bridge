from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    """
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    ALLOW_DEMO_AUTH_BYPASS: bool = False

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # OpenTelemetry & Distributed Tracing
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "kon-action-bridge"
    JAEGER_UI_URL: str = "http://localhost:16686"

    # Neon Cloud Services
    NEON_BRANCH: str = "production"
    NEON_BRANCH_ID: str = ""
    NEON_FUNCTION_HOST_SUFFIX: str = ""
    NEON_FUNCTION_URL: str = "https://br-patient-union-bdtf9eqy-hello.compute.c-8.us-east-2.aws.neon.tech/"
    NEON_REALTIME_URL: str = ""
    NEON_REALTIME_SECRET: str = ""
    NEON_AI_GATEWAY_TOKEN: str = ""
    NEON_AI_GATEWAY_BASE_URL: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./kon_action_bridge.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value:
            if value.startswith("postgres://"):
                value = value.replace("postgres://", "postgresql+asyncpg://", 1)
            elif value.startswith("postgresql://") and not value.startswith("postgresql+asyncpg://"):
                value = value.replace("postgresql://", "postgresql+asyncpg://", 1)
            if "sslmode=require" in value:
                value = value.replace("sslmode=require", "ssl=require")
            import re
            value = re.sub(r'[?&]channel_binding=[^&]+', '', value)
            if "?" not in value and "&" in value:
                value = value.replace("&", "?", 1)
        return value

    # CORS Origins (comma-separated or list)
    ALLOWED_ORIGINS: Union[str, List[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            return origins
        elif isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local", "../.env.local"],
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
