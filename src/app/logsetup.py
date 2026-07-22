import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import BASE_DIR, settings

LOG_DIR = BASE_DIR / "logs"


def setup_logging(name: str = "app") -> None:
    """Консоль + ротируемый файл. Вызывается один раз в каждой точке входа."""
    LOG_DIR.mkdir(exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        Path(LOG_DIR / f"{name}.log"), maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # шумные библиотеки — только предупреждения
    for noisy in ("httpx", "httpcore", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
