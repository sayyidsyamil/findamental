from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_files() -> tuple[str, ...]:
    files = [PROJECT_ROOT / ".env"]
    hermes_env = Path.home() / ".hermes" / ".env"
    if hermes_env.exists():
        files.append(hermes_env)
    return tuple(str(path) for path in files)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_ALLOWED_USER_ID: int | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_ALLOWED_USER_ID", "TELEGRAM_ALLOWED_USERS"),
    )
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "deepseek/deepseek-v4-flash"
    DATA_DIR: Path = Field(default=PROJECT_ROOT / "data", validation_alias="FINDAMENTAL_DATA_DIR")
    CACHE_DIR: Path = Field(
        default=PROJECT_ROOT / "data" / "extracted_cache",
        validation_alias="FINDAMENTAL_CACHE_DIR",
    )
    LOG_LEVEL: str = "INFO"

    @property
    def DEMO_FILINGS_DIR(self) -> Path:
        return self.DATA_DIR / "demo_filings"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    settings.DEMO_FILINGS_DIR.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
