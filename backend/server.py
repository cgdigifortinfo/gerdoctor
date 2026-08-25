"""Stable ASGI entry point; application composition lives in :mod:`web.application`."""
from __future__ import annotations

import sys

from web import application as _application

# Preserve the historic ``import server`` seam used by operational scripts and
# tests while keeping one authoritative module namespace for dependency swaps.
sys.modules[__name__] = _application
