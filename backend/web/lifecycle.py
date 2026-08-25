"""ASGI lifecycle composition helpers."""
from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any


def lifecycle(
    startup: Callable[[], Awaitable[None]], shutdown: Callable[[], Awaitable[None]],
) -> Any:
    @asynccontextmanager
    async def lifespan(_application: Any) -> AsyncIterator[None]:
        await startup()
        try:
            yield
        finally:
            await shutdown()
    return lifespan
