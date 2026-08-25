"""Injectable identifier-generation adapters."""
from __future__ import annotations

import uuid
from typing import Protocol


class IdentifierGenerator(Protocol):
    def new(self) -> str: ...


class Uuid4Generator:
    def new(self) -> str:
        return str(uuid.uuid4())


uuid4_generator = Uuid4Generator()
