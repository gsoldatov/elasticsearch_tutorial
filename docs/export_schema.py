import argparse
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app import create_app
from src.config import get_config, PROJECT_ROOT


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Экспорт OpenAPI-схемы приложения в JSON"
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Путь к .env файлу конфигурации (по умолчанию — .env в корне проекта)",
    )
    args = parser.parse_args()

    config = get_config(args.env_file) if args.env_file else get_config()
    app = create_app(config)
    schema = app.openapi()
    output_path = PROJECT_ROOT / "docs.json"
    output_path.write_text(
        json.dumps(schema, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"  ✓ OpenAPI-схема записана в {output_path}")


if __name__ == "__main__":
    _main()
