import os
import sys
import platform
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

_OS = platform.system()  # 'Windows', 'Darwin', 'Linux'


def get_app_data_dir() -> Path:
    """Platform-aware user config directory for Lattice."""
    if _OS == "Windows":
        d = Path.home() / "AppData" / "Roaming" / "Lattice"
    elif _OS == "Darwin":
        d = Path.home() / "Library" / "Application Support" / "Lattice"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        d = Path(xdg) / "lattice"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_env_file_path() -> Path:
    """Return .env path — app-data dir when frozen, repo root otherwise."""
    if getattr(sys, 'frozen', False):
        return get_app_data_dir() / ".env"
    return Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=get_env_file_path(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_backend: str = Field("ollama", alias="LLM_BACKEND")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_primary_model: str = Field("qwen2.5:14b", alias="OLLAMA_PRIMARY_MODEL")
    ollama_fallback_model: str = Field("qwen2.5:7b", alias="OLLAMA_FALLBACK_MODEL")
    ollama_embed_model: str = Field("nomic-embed-text", alias="OLLAMA_EMBED_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")

    # Telegram — text-in from your phone, no exposed port (bot polls Telegram outward).
    # Leave TELEGRAM_BOT_TOKEN empty to disable. Leave TELEGRAM_CHAT_ID empty and message
    # the bot once — the chat id you need shows up in the server logs.
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")

    # Paths — optional so server starts without .env for first-run setup
    vault_path: Optional[Path] = Field(None, alias="VAULT_PATH")
    vault_files_path: Optional[Path] = Field(None, alias="VAULT_FILES_PATH")
    incoming_path: Optional[Path] = Field(None, alias="INCOMING_PATH")
    db_path: Optional[Path] = Field(None, alias="DB_PATH")
    logs_path: Optional[Path] = Field(None, alias="LOGS_PATH")

    # Scheduling
    work_start: str = Field("09:00", alias="WORK_START")
    work_end: str = Field("22:00", alias="WORK_END")
    checkin_interval_minutes: int = Field(120, alias="CHECKIN_INTERVAL_MINUTES")
    daily_review_time: str = Field("21:00", alias="DAILY_REVIEW_TIME")
    nightly_maintenance_time: str = Field("23:00", alias="NIGHTLY_MAINTENANCE_TIME")
    intent_planning_interval_minutes: int = Field(30, alias="INTENT_PLANNING_INTERVAL_MINUTES")

    # Server
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8080, alias="API_PORT")
    debug: bool = Field(True, alias="DEBUG")

    # Features
    git_versioning_enabled: bool = Field(True, alias="GIT_VERSIONING_ENABLED")
    wiki_compilation_enabled: bool = Field(True, alias="WIKI_COMPILATION_ENABLED")
    self_improve_enabled: bool = Field(True, alias="SELF_IMPROVE_ENABLED")

    # Security — leave empty to disable auth (local-only trust mode)
    lattice_api_key: str = Field("", alias="LATTICE_API_KEY")

    @property
    def is_configured(self) -> bool:
        return all([self.vault_path, self.vault_files_path, self.incoming_path,
                    self.db_path, self.logs_path])

    @property
    def raw_path(self) -> Path:
        return self.vault_path / "00-raw"

    @property
    def wiki_path(self) -> Path:
        return self.vault_path / "00-wiki"

    @property
    def context_path(self) -> Path:
        return self.vault_path / "_context"

    @property
    def skills_path(self) -> Path:
        return self.vault_path / "_skills"

    def ensure_dirs(self):
        if not self.is_configured:
            return
        for p in [
            self.vault_path, self.vault_files_path, self.incoming_path,
            self.db_path.parent, self.logs_path,
            self.raw_path / "processed", self.wiki_path,
            self.context_path, self.skills_path,
        ]:
            p.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
