from __future__ import annotations

import asyncio

from .acute import acute_worker_loop


def main() -> None:
    asyncio.run(acute_worker_loop())


if __name__ == "__main__":
    main()
