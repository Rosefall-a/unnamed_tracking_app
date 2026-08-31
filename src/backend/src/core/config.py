from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    STEAMGRIDDB_API_KEY: str | None = None
    DEBUG: bool = False

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()  # type: ignore[call-arg]  # Values are loaded from the environment.