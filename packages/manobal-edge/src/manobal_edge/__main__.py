"""``python -m manobal_edge`` — Zone 1 sync + inference listener."""

from __future__ import annotations

import os

from manobal_edge.server import serve


def main() -> None:
    serve(
        os.environ.get("MANOBAL_EDGE_HOST", "127.0.0.1"),
        int(os.environ.get("MANOBAL_EDGE_PORT", "8002")),
        core_url=os.environ.get("MANOBAL_CORE_URL", "http://127.0.0.1:8000"),
        core_token=os.environ.get("MANOBAL_EDGE_TOKEN", ""),
    )


if __name__ == "__main__":
    main()
