from pathlib import Path

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


settings = Settings()
