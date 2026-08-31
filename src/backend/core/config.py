from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	DATABASE_URL: str = (
		"postgresql+psycopg://post_user:dwagshhes@db:5432/the_db"
	)
	STEAMGRIDDB_API_KEY: str | None = None
	DEBUG: bool = False

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
