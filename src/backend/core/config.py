from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	DATABASE_URL: str = (
		"postgresql+psycopg://post_user:dwagshhes@db:5432/the_db"
	)
	DEBUG: bool = False

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
