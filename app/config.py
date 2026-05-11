from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5434/reservations_db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(alias="JWT_SECRET", min_length=32)
    jwt_issuer: str = Field(default="labtrans-auth-api", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="labtrans-reservas", alias="JWT_AUDIENCE")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
