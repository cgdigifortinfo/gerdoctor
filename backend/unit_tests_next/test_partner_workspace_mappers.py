from __future__ import annotations

from slices.partner_workspace.mappers import (
    workspace_progress_from_document,
    workspace_revision_from_document,
    workspace_step_from_document,
    workspace_user_from_document,
)


def test_user_mapper_normalizes_optional_values() -> None:
    user = workspace_user_from_document({"id": "u", "name": None, "email": "e", "survey_id": 12, "notification_preferences": []})
    assert (user.id, user.name, user.email, user.survey_id, user.notification_preferences) == ("u", "", "e", "12", {})
    assert workspace_user_from_document({"_id": "mongo", "notification_preferences": {"mail": True}}).id == "mongo"
    mapped_preferences = workspace_user_from_document({"notification_preferences": {"mail": True}})
    assert mapped_preferences.notification_preferences == {"mail": True}
    empty = workspace_user_from_document({})
    assert (empty.id, empty.email, empty.survey_id) == ("", "", None)


def test_step_mapper_preserves_document_without_mongo_id() -> None:
    mapped = workspace_step_from_document({"_id": "s", "order": 2, "title": "T", "step_type": "content", "filter_tag": "medical", "description": "Help"})
    assert (mapped.id, mapped.order, mapped.title, mapped.step_type, mapped.filter_tag, mapped.description) == ("s", 2.0, "T", "content", "medical", "Help")
    assert "_id" not in mapped.document
    assert workspace_step_from_document({"id": "fallback"}).id == "fallback"
    empty = workspace_step_from_document({})
    assert (empty.id, empty.order, empty.title, empty.step_type, empty.filter_tag, empty.description) == ("", 0.0, "", "", "", "")


def test_progress_mapper_handles_valid_and_invalid_shapes() -> None:
    mapped = workspace_progress_from_document({"step_id": "s", "status": "completed", "revision": 2, "data": {"a": 1}})
    assert (mapped.step_id, mapped.status, mapped.revision, mapped.data) == ("s", "completed", 2, {"a": 1})
    assert mapped.document == {"step_id": "s", "status": "completed", "revision": 2, "data": {"a": 1}}
    empty = workspace_progress_from_document({"revision": "2", "data": []})
    assert (empty.step_id, empty.status, empty.revision, empty.data) == ("", "pending", None, {})


def test_revision_mapper_reads_actor_and_nested_data_safely() -> None:
    mapped = workspace_revision_from_document({"step_id": "s", "revision": 3, "changed_by": {"partner_id": "p"}, "data": {"x": 1}})
    assert (mapped.step_id, mapped.revision, mapped.changed_by_partner_id, mapped.data) == ("s", 3, "p", {"x": 1})
    empty = workspace_revision_from_document({"changed_by": [], "data": [], "revision": "3"})
    assert (empty.step_id, empty.revision, empty.changed_by_partner_id, empty.data) == ("", None, "", {})
    assert workspace_revision_from_document({"changed_by": {}}).changed_by_partner_id == ""
