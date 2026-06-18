from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_backend: str = Field("ollama", alias="LLM_BACKEND")
    ollama_base_url: str = Field("http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_primary_model: str = Field("qwen2.5:14b", alias="OLLAMA_PRIMARY_MODEL")
    ollama_embed_model: str = Field("nomic-embed-text", alias="OLLAMA_EMBED_MODEL")
    anthropic_api_key: str = Field("", alias="ANTHROPIC_API_KEY")

    # Paths
    vault_path: Path = Field(..., alias="VAULT_PATH")
    vault_files_path: Path = Field(..., alias="VAULT_FILES_PATH")
    incoming_path: Path = Field(..., alias="INCOMING_PATH")
    db_path: Path = Field(..., alias="DB_PATH")
    logs_path: Path = Field(..., alias="LOGS_PATH")

    # Scheduling
    work_start: str = Field("09:00", alias="WORK_START")
    work_end: str = Field("22:00", alias="WORK_END")
    checkin_interval_minutes: int = Field(120, alias="CHECKIN_INTERVAL_MINUTES")
    daily_review_time: str = Field("21:00", alias="DAILY_REVIEW_TIME")
    nightly_maintenance_time: str = Field("23:00", alias="NIGHTLY_MAINTENANCE_TIME")

    # Server
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8080, alias="API_PORT")
    debug: bool = Field(True, alias="DEBUG")

    # Features
    git_versioning_enabled: bool = Field(True, alias="GIT_VERSIONING_ENABLED")
    wiki_compilation_enabled: bool = Field(True, alias="WIKI_COMPILATION_ENABLED")
    self_improve_enabled: bool = Field(True, alias="SELF_IMPROVE_ENABLED")
    voice_enabled: bool = Field(False, alias="VOICE_ENABLED")

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
