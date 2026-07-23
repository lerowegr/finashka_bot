from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
SEED_DIR = DATA_DIR / "seed"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = ""
    db_url: str = f"sqlite+aiosqlite:///{(DATA_DIR / 'bot.db').as_posix()}"
    scrape_rps: float = 1.0
    admin_chat_id: int | None = None
    log_level: str = "INFO"

    source_base_url: str = "https://tabiturient.ru"
    # честный User-Agent: владельцы сайта могут связаться при вопросах
    user_agent: str = (
        "Mozilla/5.0 (compatible; FinashkaBot/2.0; +https://t.me/finashka_abiturient_bot)"
    )

    @field_validator("admin_chat_id", mode="before")
    @classmethod
    def _blank_to_none(cls, value):
        # пустой ADMIN_CHAT_ID= в .env означает «не задано», а не ошибку
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("db_url")
    @classmethod
    def _absolutize_sqlite(cls, value: str) -> str:
        # относительный путь к SQLite в .env (data/bot.db) делаем абсолютным от корня
        # проекта, чтобы бот работал независимо от рабочей папки запуска
        marker = ":///"
        if value.startswith("sqlite") and marker in value:
            scheme, path_part = value.split(marker, 1)
            if path_part and not Path(path_part).is_absolute():
                abs_path = (BASE_DIR / path_part).resolve().as_posix()
                return f"{scheme}{marker}{abs_path}"
        return value


settings = Settings()
