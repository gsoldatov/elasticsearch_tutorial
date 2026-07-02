import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    from src.config import get_config

    config = get_config()
    uvicorn.run(
        "src.main:app",
        host=config.backend_host,
        port=config.backend_port,
        reload=True,
    )
