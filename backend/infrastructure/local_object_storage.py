"""Filesystem-backed object storage constrained to one configured root."""
from __future__ import annotations

import logging
from pathlib import Path


class LocalStorageError(OSError): pass
class InvalidStoragePath(LocalStorageError): pass
class StoredObjectNotFound(LocalStorageError): pass


class LocalObjectStorage:
    def __init__(self, root: str, logger: logging.Logger | None = None) -> None:
        self._root = Path(root)
        self._logger = logger or logging.getLogger(__name__)

    def _path(self, path: str) -> Path:
        root = self._root.resolve()
        target = (root / path.lstrip("/")).resolve()
        if target != root and root not in target.parents:
            raise InvalidStoragePath(path)
        return target

    def initialize(self) -> str:
        self._root.mkdir(parents=True, exist_ok=True)
        self._logger.info("Local persistent storage initialized at %s", self._root)
        return "local"

    def put(self, path: str, data: bytes, content_type: str) -> int:
        self.initialize()
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return len(data)

    def get(self, path: str) -> tuple[bytes, str]:
        self.initialize()
        target = self._path(path)
        if not target.is_file():
            raise StoredObjectNotFound(path)
        return target.read_bytes(), "application/octet-stream"
