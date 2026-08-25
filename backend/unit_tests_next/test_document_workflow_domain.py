from __future__ import annotations

from slices.document_workflow.domain import resolve_document_workflow
from slices.document_workflow.mappers import document_workflow_context


LOCK = {"action": "read_only", "source_step_order": 2, "field": "files", "operator": "has_upload"}


def workflow(progress: list[dict] | None = None):  # type: ignore[no-untyped-def]
    return document_workflow_context([
        {"_id": "decision", "order": 1, "step_type": "decision", "conditions": [LOCK]},
        {"_id": "upload", "order": 2, "step_type": "form",
         "fields": [{"field_type": "multiupload"}], "conditions": [LOCK]},
        {"_id": "partner", "order": 3, "step_type": "partner_selection", "conditions": [LOCK]},
        {"_id": "documents", "order": 4, "step_type": "milestone"},
    ], progress or [])


def test_pending_workflow_exposes_unlocked_branches() -> None:
    state = resolve_document_workflow(workflow())
    assert state["decision"].as_dict() == {"read_only": False}
    assert state["upload"].read_only is False
    assert state["partner"].read_only is False
    assert state["documents"].as_dict() == {
        "documents": [], "documents_pending": True, "document_workflow": True,
    }


def test_uploaded_documents_lock_all_configured_steps_and_deduplicate() -> None:
    state = resolve_document_workflow(workflow([
        {"step_id": "upload", "status": "completed", "data": {
            "files": [
                "invalid-first", {},
                {"file_id": "one", "filename": "CV.pdf", "document_type": "CV"},
                {"file_id": "one", "filename": "duplicate.pdf"},
                {"file_id": "after-duplicate"},
            ],
            "not_a_list": "ignored",
            "files_after_invalid_field": [{"file_id": "after-invalid-field"}],
        }},
        {"step_id": "documents", "data": {"partner_uploads": [
            {"file_id": 2}, {"file_id": "three", "uploaded_by": "admin"},
        ]}},
    ]))
    assert all(state[step_id].read_only for step_id in ("decision", "upload", "partner"))
    assert state["documents"].documents_pending is False
    assert [item.as_dict() for item in state["documents"].documents] == [
        {"file_id": "one", "filename": "CV.pdf", "document_type": "CV", "uploaded_by": "user"},
        {"file_id": "after-duplicate", "filename": "Dokument", "document_type": "Dokument", "uploaded_by": "user"},
        {"file_id": "after-invalid-field", "filename": "Dokument", "document_type": "Dokument", "uploaded_by": "user"},
        {"file_id": "2", "filename": "Dokument", "document_type": "Dokument", "uploaded_by": "partner"},
        {"file_id": "three", "filename": "Dokument", "document_type": "Dokument", "uploaded_by": "admin"},
    ]


def test_only_complete_decision_blocks_form_workflows() -> None:
    incomplete = document_workflow_context([
        {"id": "before", "order": 0, "step_type": "content"},
        {"id": "decision", "order": 1, "step_type": "decision"},
        {"id": "upload", "order": 2, "step_type": "form", "fields": [{"field_type": "text"}]},
        {"id": "end", "order": 3, "step_type": "milestone"},
        {"id": "after", "order": 4, "step_type": "content"},
    ], [])
    assert resolve_document_workflow(incomplete) == {}
    upload_only = document_workflow_context([
        {"id": "d", "order": 1, "step_type": "decision"},
        {"id": "u", "order": 2, "step_type": "form", "fields": [{"field_type": "file"}]},
        {"id": "m", "order": 3, "step_type": "milestone"},
    ], [])
    partner_only = document_workflow_context([
        {"id": "d", "order": 1, "step_type": "decision"},
        {"id": "p", "order": 2, "step_type": "partner_selection"},
        {"id": "m", "order": 3, "step_type": "milestone"},
    ], [])
    assert resolve_document_workflow(upload_only) == {}
    assert resolve_document_workflow(partner_only) == {}


def test_steps_before_a_decision_do_not_abort_a_later_workflow() -> None:
    context = document_workflow_context([
        {"id": "orphan", "order": 0, "step_type": "form"},
        {"id": "orphan-milestone", "order": 0.5, "step_type": "milestone"},
        *[step.document for step in workflow().steps],
    ], [])
    assert "documents" in resolve_document_workflow(context)


def test_missing_progress_uses_pending_status_for_lock_rules() -> None:
    context = document_workflow_context([
        {"id": "d", "order": 1, "step_type": "decision", "conditions": [
            {"action": "read_only", "source_step_order": 2, "operator": "status_is", "value": "pending"}]},
        {"id": "u", "order": 2, "step_type": "form", "fields": [{"field_type": "upload"}]},
        {"id": "p", "order": 3, "step_type": "partner_selection"},
        {"id": "m", "order": 4, "step_type": "milestone"},
    ], [])
    assert resolve_document_workflow(context)["d"].read_only is True


def test_mapper_defaults_and_id_fallback_are_explicit() -> None:
    context = document_workflow_context([{"id": "s", "order": "2"}, {}], [{}, {"step_id": 3, "status": "done", "data": {"x": 1}}])
    assert (context.steps[0].id, context.steps[0].order, context.steps[0].kind) == ("s", 2.0, "")
    assert context.steps[0].document == {"id": "s", "order": "2"}
    assert (context.steps[1].id, context.steps[1].fields, context.steps[1].conditions) == ("", (), ())
    assert context.steps[1].order == 0.0
    assert (context.progress[0].step_id, context.progress[0].status, context.progress[0].data) == ("", "pending", {})
    assert (context.progress[1].step_id, context.progress[1].status, context.progress[1].data) == ("3", "done", {"x": 1})
