#!/usr/bin/env python
"""Django management entry point for the Zone 2 core service."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "manobal_core.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment problem
        msg = "Django is not installed. Run `make install` from the repository root."
        raise ImportError(msg) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
