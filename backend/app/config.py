from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://pathrix:pathrix@localhost:5432/pathrix"
    redis_url: str = "redis://localhost:6379/0"

    mapid_basemap_key: str = ""
    mapid_mission_api_key: str = ""
    # geoserver.mapid.io publishes project vector layers under its own key,
    # separate from the mission API key.
    mapid_geoserver_api_key: str = ""
    mapid_project_id: str = ""
    mapid_halte_layer_id: str = ""

    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    # MAPID Routing is a separate product from the basemap/mission/geoserver
    # keys above — a different base URL, auth, and contract entirely (see
    # docs/CLAUDE_TRANSIT_HANDOFF.md). Defaults leave current behavior
    # (local-OSM-only road-leg geometry) unchanged until a real contract is
    # verified and wired in `app/data/mapid_routing.py`.
    mapid_routing_base_url: str = ""
    mapid_routing_api_key: str = ""
    mapid_routing_enabled: bool = False
    mapid_routing_timeout_s: float = 5.0

    # Swaps calculate_route for a hand-authored fixture (app/agent/demo_route.py)
    # — real bus topology is empty across the dataset today, so this is for
    # recording a demo only. Default off; never enable in a real deployment.
    demo_mock_route: bool = False

    study_area_polygon: str = ""

    rate_limit_per_minute: int = 60

    # Comma-separated browser origins allowed to call this API cross-origin
    # (the frontend is deployed separately, e.g. on Vercel). Vite's dev
    # server proxies /api and /ws itself, so localhost is only needed for a
    # production-mode build served from a different port locally.
    cors_allow_origins: str = "http://localhost:5173"

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


settings = Settings()
