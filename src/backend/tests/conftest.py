"""Pytest bootstrap for backend tests.

The application persists its Fernet key during Settings import. Production
uses /data (or APP_DATA_DIR) for that persistent state, but the CI test runner
must not depend on a Docker-mounted production volume. Give pytest its own
writable, process-local data directory before any application modules import
Settings.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


os.environ.setdefault(
    "APP_DATA_DIR",
    str(Path(tempfile.gettempdir()) / f"unnamed_tracking_app-pytest-{os.getpid()}"),
)
