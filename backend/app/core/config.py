

from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Aplicacion
    APP_NAME: str = "SalesIA Enterprise"
    ENVIRONMENT: str = "development"

    # PostgreSQL / Supabase
    DATABASE_URL: str

    # Base exclusiva para pruebas
    TEST_DATABASE_URL: str | None = None

    # Pool PostgreSQL configurable segun el plan de Railway
    DB_POOL_SIZE: int = Field(default=2, ge=1, le=30)
    DB_MAX_OVERFLOW: int = Field(default=1, ge=0, le=30)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, le=120)

    # Proteccion opcional para demostraciones con una base de testing especifica.
    DEMO_EXPECTED_SUPABASE_REF: str | None = None

    # Frontend: origenes separados por comas
    CORS_ORIGINS: str = "http://localhost:5173"

    # Seguridad JWT
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        le=1440,
    )

    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=30,
    )

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validar_algoritmo_jwt(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("JWT_ALGORITHM debe ser HS256.")
        return value

    @field_validator("ENVIRONMENT")
    @classmethod
    def validar_entorno(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in {"development", "testing", "production"}:
            raise ValueError(
                "ENVIRONMENT debe ser development, "
                "testing o production."
            )

        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validar_produccion(self):
        if self.DEMO_EXPECTED_SUPABASE_REF:
            from scripts.verificar_aislamiento_real import obtener_referencia_supabase
            expected = self.DEMO_EXPECTED_SUPABASE_REF.strip()
            actual = obtener_referencia_supabase(self.DATABASE_URL)
            if not actual or actual != expected:
                raise ValueError("SEGURIDAD DEMO: DATABASE_URL no pertenece al proyecto Supabase autorizado.")

        if not self.cors_origins_list:
            raise ValueError(
                "Debe configurarse al menos un origen CORS."
            )

        if self.ENVIRONMENT == "production":
            for origin in self.cors_origins_list:
                parsed = urlsplit(origin)

                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.path not in ("", "/")
                    or parsed.query
                    or parsed.fragment
                    or parsed.username
                    or parsed.password
                ):
                    raise ValueError(
                        "En production, cada CORS_ORIGINS "
                        "debe ser un origen HTTPS válido "
                        "(sin rutas ni parámetros)."
                    )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
