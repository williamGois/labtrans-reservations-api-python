from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg2://postgres@localhost:5434/reservations_db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(alias="JWT_SECRET", min_length=32)
    jwt_issuer: str = Field(default="labtrans-auth-api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="labtrans-reservas", alias="JWT_AUDIENCE")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )
    app_environment: str = Field(default="Development", alias="APP_ENVIRONMENT")
    otel_service_name: str = Field(
        default="labtrans-reservations-api-python", alias="OTEL_SERVICE_NAME"
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317", alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_traces_exporter: str = Field(default="none", alias="OTEL_TRACES_EXPORTER")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
