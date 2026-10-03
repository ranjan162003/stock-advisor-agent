"""Central, typed application settings.

Every value can be overridden with an environment variable prefixed
`STOCK_ADVISOR_` (e.g. `STOCK_ADVISOR_OLLAMA_DEFAULT_MODEL=qwen2.5`) or via a
`backend/.env` file — see `.env.example`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_DATA_DIR = BACKEND_ROOT_DIR / "data"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT_DIR / ".env",
        env_prefix="STOCK_ADVISOR_",
        extra="ignore",
    )

    app_name: str = "Stock Advisor Agent API"
    database_url: str = f"sqlite:///{(LOCAL_DATA_DIR / 'stock_advisor.db').as_posix()}"
    cors_allowed_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Market data ---
    price_history_period: str = "1y"
    market_data_cache_ttl_minutes: int = 360
    news_headlines_per_stock: int = 4
    market_data_fetch_workers: int = 8
    finnhub_api_key: str | None = None

    # --- Agent ---
    max_candidates_sent_to_llm: int = 12
    # Local models are slower and follow long prompts less reliably — give them fewer.
    max_candidates_sent_to_local_llm: int = 8
    max_stocks_per_recommendation: int = 6
    llm_timeout_seconds: int = 240
    ollama_timeout_seconds: int = 600

    # --- LLM providers ---
    claude_default_model: str = "claude-opus-5-5"
    gemini_default_model: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.1"


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
