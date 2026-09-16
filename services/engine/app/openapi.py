from __future__ import annotations

import json
from pathlib import Path

from .main import app


def write_openapi() -> Path:
    destination = Path(__file__).resolve().parents[1] / "openapi.json"
    destination.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


if __name__ == "__main__":
    print(write_openapi())
