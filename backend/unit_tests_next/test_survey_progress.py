import pytest

from slices.survey_runtime.progress import (
    MissingMultiUpload, MissingRequiredFields, MissingRequiredUploads, validate_completion,
)

CONTENT = frozenset({"content"})


def test_completion_accepts_required_values_and_uploads():
    step = {"required_fields": ["name", "name"], "required_uploads": ["passport"], "fields": [
        {"name": "name", "label": "Name", "field_type": "text", "required": True},
        {"name": "intro", "field_type": "content", "required": True},
        {"name": "files", "label": "Files", "field_type": "multiupload", "required": True},
    ]}
    validate_completion(step, {"name": "Yilmaz", "files": [
        {"file_id": "f-1", "document_type": "passport"},
    ]}, CONTENT)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_completion_reports_missing_required_field(value):
    step = {"fields": [{"name": "name", "label": "Full name", "field_type": "text", "required": True}]}
    with pytest.raises(MissingRequiredFields) as caught:
        validate_completion(step, {"name": value}, CONTENT)
    assert caught.value.labels == ["Full name"]


def test_completion_uses_field_name_when_label_is_absent():
    with pytest.raises(MissingRequiredFields) as caught:
        validate_completion({"required_fields": ["external"], "fields": []}, {}, CONTENT)
    assert caught.value.labels == ["external"]


def test_completion_reports_missing_document_type():
    step = {"required_uploads": ["passport"], "fields": [
        {"name": "files", "field_type": "multiupload"},
    ]}
    with pytest.raises(MissingRequiredUploads) as caught:
        validate_completion(step, {"files": [{"file_id": "f-1"}, "invalid"]}, CONTENT)
    assert caught.value.document_types == ["passport"]


@pytest.mark.parametrize("entries", [None, {}, [], [{"document_type": "passport"}]])
def test_completion_requires_a_file_in_required_multiupload(entries):
    step = {"fields": [{"name": "files", "field_type": "multiupload", "required": True}]}
    with pytest.raises(MissingMultiUpload) as caught:
        validate_completion(step, {"files": entries}, CONTENT)
    assert caught.value.label == "files"
