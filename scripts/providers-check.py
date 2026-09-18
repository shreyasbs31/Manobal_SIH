#!/usr/bin/env python3
"""Call each real provider once. Prefer the engine container. Never print secrets."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "services" / "engine") not in sys.path:
    sys.path.insert(0, str(ROOT / "services" / "engine"))

from app.providers.probe import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
