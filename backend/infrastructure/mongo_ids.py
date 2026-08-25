"""MongoDB identifier conversion without HTTP concerns."""
from __future__ import annotations

from bson import ObjectId
from collections.abc import Iterable


def object_id_or_none(value: object) -> ObjectId | None:
    text = str(value or "")  # pragma: no mutate - every falsy fallback is an invalid ObjectId
    return ObjectId(text) if ObjectId.is_valid(text) else None


def valid_object_ids(values: Iterable[object]) -> tuple[ObjectId, ...]:
    return tuple(object_id for value in values if (object_id := object_id_or_none(value)) is not None)
