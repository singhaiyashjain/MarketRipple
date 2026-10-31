"""Settings loaded from .env (see ../.env.example). OWNER: M3"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]        # repo root
DATA_DIR = ROOT / "data"
CONTRACTS_DIR = ROOT / "contracts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""
    # backup provider, used automatically if the primary call fails
    fallback_provider: str = "none"
    fallback_api_key: str = ""
    fallback_model: str = ""
    # MongoDB (saved analyses + recurring-news log). Empty = not configured (analyses are not saved, alerts live in memory)
    mongodb_uri: str = ""
    mongodb_db: str = "finpulse"
    force_mock: bool = False
    use_llm_cache: bool = True
    max_path_len: int = 5
    top_k_paths: int = 10
    max_nodes: int = 25          # readable graph: cap visible nodes
    # live monitor
    live_enabled: bool = True
    live_poll_seconds: int = 300
    live_max_events_per_poll: int = 2          # analysed events created per REGION per poll
    live_max_attempts_per_region: int = 6      # headlines tried per region per poll (limits LLM calls)
    replay_interval_seconds: int = 20
    # recurring-news alerts (stars that blink)
    recur_window_days: int = 7          # look-back window for "frequent" news
    recur_alert_hits: int = 3           # >= this many distinct negative stories in the window => star blinks (alert)
    recur_watch_hits: int = 2           # >= this many => amber "watch"
    recur_half_life_days: float = 3.0   # older stories count less in the decayed score
    news_api_provider: str = "none"   # none | newsapi
    news_api_key: str = ""
    # login + admin panel (users live in MongoDB collection "users"; in memory if MONGODB_URI is empty)
    auth_secret: str = ""             # signs login tokens. Set a long random value on Render, or logins end on every restart
    auth_required: bool = False       # True = every /api data route needs a valid login token
    auth_token_hours: int = 12
    admin_username: str = ""          # bootstrap admin, created/updated at startup (needs both values)
    admin_password: str = ""
    auth_max_failures: int = 5        # wrong passwords before a short lockout
    auth_lockout_seconds: int = 300


settings = Settings()
