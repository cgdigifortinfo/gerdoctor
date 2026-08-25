from __future__ import annotations

from slices.partner_selection.mappers import (
    selectable_partner_from_document,
    selection_step_from_document,
    selection_user_from_document,
)
from slices.partner_selection.models import SelectionKind


def test_user_mapper_normalizes_ids_and_optional_survey() -> None:
    mapped = selection_user_from_document({"_id": 1, "survey_id": 2})
    assert (mapped.id, mapped.survey_id) == ("1", "2")
    fallback = selection_user_from_document({"id": "u"})
    assert (fallback.id, fallback.survey_id) == ("u", None)
    assert selection_user_from_document({}).id == ""


def test_step_mapper_only_accepts_selection_kinds() -> None:
    single = selection_step_from_document({"_id": "s", "step_type": "partner_selection", "survey_id": "survey", "filter_tag": "medical"})
    assert single is not None
    assert (single.id, single.kind, single.survey_id, single.filter_tag) == ("s", SelectionKind.SINGLE, "survey", "medical")
    assert single.document["step_type"] == "partner_selection"
    multi = selection_step_from_document({"id": "m", "step_type": "partner_multiselection"})
    assert multi is not None and multi.id == "m" and multi.kind is SelectionKind.MULTIPLE and multi.survey_id is None and multi.filter_tag == ""
    missing_id = selection_step_from_document({"step_type": "partner_selection"})
    assert missing_id is not None and missing_id.id == ""
    assert selection_step_from_document({"step_type": "content"}) is None
    assert selection_step_from_document({}) is None


def test_partner_mapper_normalizes_tags_activity_and_document() -> None:
    mapped = selectable_partner_from_document({"_id": "p", "name": "Name", "tags": [1, "medical"], "is_active": True})
    assert (mapped.id, mapped.name, mapped.tags, mapped.active) == ("p", "Name", frozenset({"1", "medical"}), True)
    assert mapped.document["name"] == "Name"
    empty = selectable_partner_from_document({"id": "fallback", "tags": "bad", "is_active": 1})
    assert (empty.id, empty.name, empty.tags, empty.active) == ("fallback", "", frozenset(), False)
    assert selectable_partner_from_document({}).id == ""
