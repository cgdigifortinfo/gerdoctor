from bson import ObjectId

from server import _document_workflow_state


def _workflow():
    locks = [
        {"action": "read_only", "source_step_order": 8, "field": "documents", "operator": "has_upload", "value": ""},
        {"action": "read_only", "source_step_order": 10, "field": "partner_uploads", "operator": "has_upload", "value": ""},
    ]
    return [
        {"_id": ObjectId("64b000000000000000000001"), "order": 7, "step_type": "decision", "conditions": locks},
        {"_id": ObjectId("64b000000000000000000002"), "order": 8, "step_type": "form", "fields": [{"name": "documents", "field_type": "multiupload"}], "conditions": locks},
        {"_id": ObjectId("64b000000000000000000003"), "order": 9, "step_type": "partner_selection", "fields": [], "conditions": locks},
        {"_id": ObjectId("64b000000000000000000004"), "order": 10, "step_type": "milestone", "fields": []},
    ]


def test_user_upload_is_exposed_on_common_document_step_and_locks_prior_steps():
    state = _document_workflow_state(_workflow(), [{
        "step_id": "64b000000000000000000002",
        "data": {"documents": [{"file_id": "user-file", "filename": "fsp.pdf", "document_type": "Diplom"}]},
    }])
    assert state["64b000000000000000000004"]["documents"] == [{
        "file_id": "user-file", "filename": "fsp.pdf", "document_type": "Diplom", "uploaded_by": "user",
    }]
    assert all(state[f"64b00000000000000000000{number}"]["read_only"] for number in (1, 2, 3))


def test_partner_upload_uses_same_document_step_and_deduplicates_files():
    upload = {"file_id": "partner-file", "filename": "bescheid.pdf", "uploaded_by": "partner"}
    state = _document_workflow_state(_workflow(), [{
        "step_id": "64b000000000000000000004", "data": {"partner_uploads": [upload, upload]},
    }])
    documents = state["64b000000000000000000004"]["documents"]
    assert len(documents) == 1
    assert documents[0]["uploaded_by"] == "partner"
    assert state["64b000000000000000000001"]["read_only"] is True


def test_pending_document_step_does_not_lock_branch_before_any_upload():
    state = _document_workflow_state(_workflow(), [])
    assert state["64b000000000000000000004"]["documents_pending"] is True
    assert state["64b000000000000000000001"]["read_only"] is False
