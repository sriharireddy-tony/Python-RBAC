from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SaaS RBAC API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    database_url: str

    # --- authentication -------------------------------------------------
    # secret_key has no default on purpose: a default would inevitably ship
    # to production, and anyone holding it can mint valid tokens.
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
