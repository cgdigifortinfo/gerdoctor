"""Fast unit tests for deterministic versioning helpers.

Database orchestration is covered separately in tests/test_step_answer_versioning.py.
"""
from bson import ObjectId

from slices.step_versioning.models import MigrationStats
from slices.step_versioning.domain import (
    answer_history_item, document_binding, file_references, progress_revision_plan,
    snapshot_hash, step_snapshot, step_version_document,
)
from infrastructure.mongo_serialization import mongo_json_safe


def test_json_safe_recursively_serializes_object_ids_and_removes_mongo_ids():
    object_id = ObjectId()

    result = mongo_json_safe({"_id": ObjectId(), "owner": object_id, "nested": [{"value": object_id}]})

    assert result == {"owner": str(object_id), "nested": [{"value": str(object_id)}]}


def test_step_snapshot_keeps_configuration_but_removes_mutable_metadata():
    step = {
        "_id": ObjectId(),
        "title": "Damals",
        "fields": [{"name": "answer", "label": "Antwort"}],
        "current_version": 4,
        "updated_at": "later",
        "deleted_at": "later",
        "deleted_by": {"email": "admin@example.com"},
    }

    snapshot = step_snapshot(mongo_json_safe(step))

    assert snapshot == {
        "title": "Damals",
        "fields": [{"name": "answer", "label": "Antwort"}],
    }


def test_snapshot_hash_is_stable_for_different_dictionary_order():
    assert snapshot_hash({"title": "A", "order": 1}) == snapshot_hash({"order": 1, "title": "A"})
    assert snapshot_hash({"title": "A"}) != snapshot_hash({"title": "B"})
    assert snapshot_hash({"title": "A", "order": 1}) == "b3bccc8870a3441ee8c1a8bcb533ccba79fd7b74cfae71c4281948ed250231ec"
    assert snapshot_hash({"title": "Ärztin"}) == "8ce1eff4c4fbdb49ae9564fc5782c3e675c3972e34d3542e7dfaf315a65f9401"


def test_file_references_find_nested_uploads_and_report_their_paths():
    data = {
        "documents": [{"file_id": "user-file", "filename": "user.pdf"}],
        "nested": {"partner_uploads": [{"file_id": "partner-file"}]},
        "ignored": ["text", {"without_file": True}],
    }

    references = list(file_references(data))

    assert references == [
        ("data.documents[0]", {"file_id": "user-file", "filename": "user.pdf"}),
        ("data.nested.partner_uploads[0]", {"file_id": "partner-file"}),
    ]


def test_version_and_progress_documents_are_deterministic_and_immutable():
    step = {"title": "Title", "current_version": 2, "order": 3, "survey_id": "survey"}
    version = step_version_document("step", step, 2, {"id": "admin"}, "update", "now")
    assert version == {
        "step_id": "step", "version": 2,
        "snapshot": {"title": "Title", "order": 3, "survey_id": "survey"},
        "snapshot_hash": snapshot_hash({"title": "Title", "order": 3, "survey_id": "survey"}),
        "change_type": "update", "created_at": "now", "created_by": {"id": "admin"},
    }

    original_data = {"files": [{"file_id": "f"}]}
    plan = progress_revision_plan(
        existing={"started_at": "before"}, step={"id": "s"}, user_id="u", status="completed",
        data=original_data, step_version=2, revision=3, actor=None, change_type="update",
        changed_at="now", extra_fields={"temporary": True}, unset_fields=["temporary"],
    )
    original_data["files"].clear()
    assert plan.current == {
        "user_id": "u", "step_id": "s", "survey_id": None, "step_order": 0,
        "status": "completed", "data": {"files": [{"file_id": "f"}]},
        "step_version": 2, "revision": 3, "started_at": "before", "updated_at": "now",
    }
    assert plan.revision == {
        **plan.current, "created_at": "now", "change_type": "update", "changed_by": {},
    }
    assert plan.unset_fields == ("temporary",)

    fallback = progress_revision_plan(
        existing={"data": {"kept": True}}, step={"id": "s"}, user_id="u", status="active",
        data=None, step_version=1, revision=1, actor={"role": "user"}, change_type="start",
        changed_at="now",
    )
    assert fallback.current["data"] == {"kept": True} and fallback.current["started_at"] == "now"
    object_id_plan = progress_revision_plan(
        existing=None, step={"_id": "object-id", "id": "public-id", "survey_id": "survey", "order": 9},
        user_id="doctor", status="pending", data={}, step_version=7, revision=8,
        actor={}, change_type="migration", changed_at="later", extra_fields={"completed_at": "done"},
    )
    assert object_id_plan.current == {
        "user_id": "doctor", "step_id": "object-id", "survey_id": "survey", "step_order": 9,
        "status": "pending", "data": {}, "step_version": 7, "revision": 8,
        "started_at": "later", "updated_at": "later", "completed_at": "done",
    }
    missing_unset = progress_revision_plan(
        existing=None, step={"id": "s"}, user_id="u", status="active", data={}, step_version=1,
        revision=1, actor=None, change_type="update", changed_at="now", unset_fields=["absent"],
    )
    assert "absent" not in missing_unset.current


def test_document_binding_resolves_upload_origin_and_filename():
    revision = {"user_id": "u", "step_id": "s", "step_version": 2, "revision": 4, "created_at": "now"}
    partner = document_binding(revision, "data.partner_uploads[0]", {"file_id": 7, "name": "a.pdf"})
    user = document_binding(revision, "data.files[0]", {"file_id": "8", "filename": "b.pdf", "uploaded_by": "admin"})
    detailed = document_binding(revision, "data.files[1]", {
        "file_id": "9", "document_type": "license", "filename": "c.pdf", "partner_id": "p",
    })
    assert partner == {
        "file_id": "7", "user_id": "u", "step_id": "s", "step_version": 2,
        "progress_revision": 4, "field_path": "data.partner_uploads[0]",
        "document_type": None, "filename": "a.pdf", "uploaded_by": "partner",
        "partner_id": None, "created_at": "now", "historical_protected": True,
    }
    assert user == {**partner, "file_id": "8", "field_path": "data.files[0]", "filename": "b.pdf", "uploaded_by": "admin"}
    assert detailed == {
        **partner, "file_id": "9", "field_path": "data.files[1]", "document_type": "license",
        "filename": "c.pdf", "uploaded_by": "user", "partner_id": "p",
    }


def test_history_marks_changed_deleted_and_unchanged_configurations():
    snapshot = {"title": "Old", "fields": [{"name": "removed"}, {"name": "kept"}]}
    historical = {"snapshot": snapshot, "snapshot_hash": snapshot_hash(snapshot)}
    row = {"step_id": "s", "step_version": 1}
    changed = answer_history_item(row, {"title": "New", "current_version": 2, "fields": [{"name": "kept"}]}, historical)
    assert changed == {
        **row, "step_title": "Old", "current_step_version": 2,
        "configuration_changed": True, "step_deleted": False, "step_snapshot": snapshot,
        "removed_field_names": ["removed"],
    }
    unchanged = answer_history_item(row, {**snapshot, "current_version": 1}, historical)
    assert unchanged == {
        **row, "step_title": "Old", "current_step_version": 1,
        "configuration_changed": False, "step_deleted": False, "step_snapshot": snapshot,
        "removed_field_names": [],
    }
    deleted = answer_history_item(row, None, None)
    assert deleted["step_deleted"] is True and deleted["step_title"] == "Gelöschter Schritt"
    deleted_at_version = answer_history_item({"step_id": "s", "step_version": 6}, None, {
        "snapshot": {"title": "Archived", "fields": [{"label": "unnamed"}]},
    })
    assert deleted_at_version["current_step_version"] == 6
    assert deleted_at_version["step_title"] == "Archived" and deleted_at_version["removed_field_names"] == []
    same_version_changed = answer_history_item(row, {
        "title": "Live", "current_version": 1, "fields": [], "is_deleted": True,
    }, historical)
    assert same_version_changed["configuration_changed"] is True
    assert same_version_changed["step_deleted"] is True
    content_only_changed = answer_history_item(row, {
        "title": "Live title", "current_version": 1, "fields": [{"name": "kept"}],
    }, historical)
    assert content_only_changed["configuration_changed"] is True
    assert content_only_changed["step_deleted"] is False
    live_title = answer_history_item(
        {"step_id": "s", "step_version": 1},
        {"title": "Live title", "current_version": 1, "fields": []},
        {"snapshot": {"fields": []}, "snapshot_hash": snapshot_hash({"title": "Live title", "fields": []})},
    )
    assert live_title["step_title"] == "Live title" and live_title["configuration_changed"] is False
    default_version = answer_history_item({"step_id": "s"}, None, None)
    assert default_version["current_step_version"] == 1
    deleted_snapshot = {"title": "Deleted", "fields": [], "is_deleted": True}
    deletion_only = answer_history_item(row, {**deleted_snapshot, "current_version": 1}, {
        "snapshot": deleted_snapshot, "snapshot_hash": snapshot_hash(deleted_snapshot),
    })
    assert deletion_only["configuration_changed"] is True and deletion_only["step_deleted"] is True


def test_migration_stats_have_stable_public_shape():
    assert MigrationStats(1, 2, 3).as_dict() == {"steps": 1, "answers": 2, "documents": 3}
