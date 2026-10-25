"""Vercel Python entry point for the Toyota NextMove FastAPI application."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_SOURCE = Path(__file__).resolve().parents[1] / "backend" / "src"
if str(BACKEND_SOURCE) not in sys.path:
    sys.path.insert(0, str(BACKEND_SOURCE))

from nextmove.main import app  # noqa: F401
