from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://pathrix:pathrix@localhost:5432/pathrix"
    redis_url: str = "redis://localhost:6379/0"

    mapid_basemap_key: str = ""
    mapid_mission_api_key: str = ""

    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    study_area_polygon: str = ""

    rate_limit_per_minute: int = 60


settings = Settings()
