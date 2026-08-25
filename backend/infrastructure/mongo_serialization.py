"""Conversion of MongoDB values into JSON-safe data at the technical boundary."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bson import ObjectId


def mongo_json_safe(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): mongo_json_safe(item) for key, item in value.items() if key != "_id"}
    if isinstance(value, (list, tuple)):
        return [mongo_json_safe(item) for item in value]
    return value
