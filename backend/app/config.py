from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    supabase_db_url: str
    anthropic_api_key: str | None = None  # Optional: only needed for /recommend reranking
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    
    dd_api_key: str | None = None
    dd_service: str = "movie-rec-backend"
    dd_env: str = "dev"
    dd_version: str | None = None
    dd_site: str = "datadoghq.com"
    dd_llmobs_ml_app: str | None = None  # Falls back to dd_service when unset
    # Only enable tracing when explicitly requested AND ddtrace is available
    # This prevents agent connection attempts when disabled
    dd_trace_enabled: bool = False
    dd_trace_agent_url: str | None = None  # Override agent URL (for local development with agent)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
