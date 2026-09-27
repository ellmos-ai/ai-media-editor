"""Core package helpers for :mod:`ai_media_editor`."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_home() -> Path:
    """Return the user-data root, defaulting to the current working directory."""
    return Path(os.environ.get("AI_MEDIA_EDITOR_HOME", ".")).resolve()
