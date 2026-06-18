import sys
from pathlib import Path
from loguru import logger
from config.settings import get_settings


def setup_logger():
    settings = get_settings()
    logs_path = settings.logs_path
    logs_path.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        sys.stderr,
        level="DEBUG" if settings.debug else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )

    logger.add(
        logs_path / "lattice.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )

    logger.add(
        logs_path / "llm.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        filter=lambda r: "llm" in r["name"],
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
    )

    return logger


def get_logger(name: str):
    return logger.bind(name=name)
