from pathlib import Path

from src.models.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_config(env_path: str | Path | None = None) -> Config:
    """Загружает и валидирует конфигурацию из .env файла.

    Параметры:
        env_path: Путь к .env файлу. Абсолютный или относительно PROJECT_ROOT.
                  По умолчанию — .env в корне проекта.
    """
    if env_path is None:
        resolved = PROJECT_ROOT / ".env"
    else:
        resolved = Path(env_path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved

    if not resolved.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {resolved}")

    return Config(_env_file=resolved)
