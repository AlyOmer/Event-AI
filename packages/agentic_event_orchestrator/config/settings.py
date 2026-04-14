from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database — accepts plain postgresql:// and auto-converts to asyncpg driver
    database_url: str = ""
    app_database_url: str = ""  # pooled URL from .env (APP_DATABASE_URL)

    @property
    def async_database_url(self) -> str:
        """Return asyncpg-compatible URL, preferring APP_DATABASE_URL."""
        url = self.app_database_url or self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Gemini / LLM
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-2.5-flash"  # matches GEMINI_MODEL in .env

    # Backend API
    backend_api_url: str = "http://localhost:3001/api/v1"

    # Mem0
    mem0_api_key: str = ""

    # Service auth
    ai_service_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    # Rate limiting
    rate_limit_per_minute: int = 30

    # Session
    session_ttl_days: int = 30

    # Agent safety
    max_handoff_depth: int = 5
    max_response_chars: int = 2000  # tighter cap — keeps responses concise

    # Prompt injection firewall
    injection_blocklist_path: str = "data/injection_blocklist.yaml"
    max_input_chars: int = 2000
    promptguard_threshold: float = 0.85
    alignment_threshold: float = 0.80

    # TruLens RAG evaluation
    trulens_enabled: bool = False
    trulens_groundedness_threshold: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
