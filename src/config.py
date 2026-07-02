from pathlib import Path

from src.models.config import Config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_env_path(env_path: str | Path | None = None) -> Path:
    """Определяет абсолютный путь к .env файлу.

    Параметры:
        env_path: Путь к .env файлу. Абсолютный или относительно PROJECT_ROOT.
                  По умолчанию — .env в корне проекта.
    """
    if env_path is None:
        return PROJECT_ROOT / ".env"
    resolved = Path(env_path)
    if not resolved.is_absolute():
        return PROJECT_ROOT / resolved
    return resolved


def get_config(env_path: str | Path | None = None) -> Config:
    """Загружает и валидирует конфигурацию из .env файла.

    Параметры:
        env_path: Путь к .env файлу. Абсолютный или относительно PROJECT_ROOT.
                  По умолчанию — .env в корне проекта.
    """
    resolved = _resolve_env_path(env_path)

    if not resolved.exists():
        raise FileNotFoundError(f"Файл конфигурации не найден: {resolved}")

    return Config(_env_file=resolved)
