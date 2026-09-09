"""WSGI entry point for the identity enclave."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "manobal_identity.settings.local")

application = get_wsgi_application()
