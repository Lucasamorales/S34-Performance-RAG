from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
	openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
	database_url: str = Field(..., alias="DATABASE_URL")
	database_direct_url: Optional[str] = Field(None, alias="DATABASE_DIRECT_URL")
	supabase_schema: str = Field("public", alias="SUPABASE_SCHEMA")

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
	)


settings = Settings()

