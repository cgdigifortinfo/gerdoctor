from __future__ import annotations

import pytest

from slices.step_configuration.domain import (
    _option_name, condition_leaves, normalize_document, normalize_field, prepare_create, prepare_update,
    relation_issues, required_field_names,
)


@pytest.mark.parametrize(("field", "expected"), [
    ({"field_type": "UNKNOWN", "label": "Full Name", "required": 1, "width": "bad"},
     {"field_type": "text", "name": "full_name", "id": "full_name", "label": "Full Name", "required": True, "width": "full", "help_text": ""}),
    ({"field_type": "textarea", "rows": 99, "name": "bio"}, {"rows": 20}),
    ({"field_type": "heading", "required": True, "heading_level": 1, "content": "Title"},
     {"required": False, "heading_level": 2, "content": "Title"}),
    ({"field_type": "image", "label": "Portrait"}, {"image_url": "", "alt_text": "Portrait", "caption": ""}),
    ({"field_type": "multiupload", "options": None},
     {"options": [], "multiple": True, "accept": ".pdf,.png,.jpg,.jpeg,.doc,.docx"}),
])
def test_field_normalization_variants(field: dict, expected: dict) -> None:
    normalized = normalize_field(field)
    for key, value in expected.items():
        assert normalized[key] == value


def test_field_fallbacks_bounds_and_custom_metadata() -> None:
    assert normalize_field({})["name"] == "text_1"
    normalized = normalize_field({"field_type": "textarea", "rows": "bad", "custom": 1}, 2)
    assert (normalized["name"], normalized["rows"], normalized["custom"]) == ("textarea_3", 4, 1)
    upload = normalize_field({"field_type": "file", "multiple": False, "accept": ".pdf"})
    assert (upload["multiple"], upload["accept"]) == (False, ".pdf")
    assert normalize_field({"field_type": "file", "multiple": True})["multiple"] is True
    assert normalize_field({"field_type": "text", "width": "full"})["width"] == "full"
    assert normalize_field({"field_type": "text", "width": "third"})["width"] == "third"
    for kind in ("heading", "paragraph", "html"):
        assert normalize_field({"field_type": kind, "content": "Body"})["content"] == "Body"
        assert normalize_field({"field_type": kind, "label": "From label"})["content"] == "From label"
        assert normalize_field({"field_type": kind, "label": "Label", "content": "Content"})["content"] == "Content"
    assert normalize_field({"field_type": "image"})["alt_text"] == "image_1"


def test_normalized_field_is_an_exact_persistence_contract() -> None:
    assert normalize_field({"field_type": "select", "label": "Ärztliche Wahl", "options": ["A"],
                            "width": "half", "help_text": "Hilfe", "id": "fixed"}, 4) == {
        "field_type": "select", "label": "Ärztliche Wahl", "options": ["A"],
        "width": "half", "help_text": "Hilfe", "id": "fixed",
        "name": "rztliche_wahl", "required": False,
    }
    assert normalize_field({"field_type": "image", "name": "photo", "content": "Fallback",
                            "image_url": "/x", "alt_text": "Alt", "caption": "Cap"}) == {
        "field_type": "image", "name": "photo", "content": "Fallback", "image_url": "/x",
        "alt_text": "Alt", "caption": "Cap", "id": "photo", "label": "Fallback",
        "required": False, "width": "full", "help_text": "",
    }


def test_document_and_required_fields_are_canonical_and_deduplicated() -> None:
    document = normalize_document({"fields": [{"label": "Name", "required": True}]})
    assert document["form_schema_version"] == 1
    assert required_field_names(document["fields"], ["name", "external"]) == ["name", "external"]
    excluded = [
        normalize_field({"field_type": "heading", "name": "heading", "required": True}),
        normalize_field({"field_type": "multiupload", "name": "docs", "required": True}),
    ]
    assert required_field_names(excluded, []) == []
    original = {"fields": [{"label": "Before"}]}
    normalized = normalize_document(original)
    normalized["fields"][0]["label"] = "After"
    assert original["fields"][0]["label"] == "Before"
    indexed = normalize_document({"fields": [{}, {}]})
    assert [field["name"] for field in indexed["fields"]] == ["text_1", "text_2"]


def test_create_and_update_changes_encode_defaults_and_explicit_unset() -> None:
    created = prepare_create({
        "title": "Step", "fields": [{"label": "Name", "required": True}],
        "required_fields": [], "filter_tag": None, "conditions": None,
    }, "survey", "now")
    assert created.values["survey_id"] == "survey"
    assert created.values["required_fields"] == ["name"]
    assert created.values["filter_tag"] == "" and created.values["conditions"] == []
    assert created.values["translations"] == {} and created.values["created_at"] == "now"
    assert created.values["is_active"] is True and created.values["is_deleted"] is False
    assert created.values == {
        "title": "Step",
        "fields": [{"label": "Name", "required": True, "field_type": "text", "name": "name",
                    "id": "name", "width": "full", "help_text": ""}],
        "required_fields": ["name"], "filter_tag": "", "conditions": [],
        "survey_id": "survey", "form_schema_version": 1, "is_active": True,
        "is_deleted": False, "current_version": 1, "created_at": "now",
        "skip_label": "", "action_label": "", "pending_message": "", "complete_message": "",
        "email_subject_enter": "", "email_body_enter": "", "email_subject_edit": "",
        "email_body_edit": "", "email_subject_leave": "", "email_body_leave": "",
        "required_uploads": [], "field_mappings": [], "translations": {},
    }
    updated = prepare_update(
        {"fields": [{"label": "Email", "required": True}], "required_fields": [],
         "partner_user_fee_cents": None, "title": None},
        frozenset({"fields", "required_fields", "partner_user_fee_cents"}),
    )
    assert updated.values["required_fields"] == ["email"]
    assert "title" not in updated.values
    assert updated.unset_fields == ("partner_user_fee_cents",)
    assert updated.values == {
        "fields": [{"label": "Email", "required": True, "field_type": "text", "name": "email",
                    "id": "email", "width": "full", "help_text": ""}],
        "required_fields": ["email"], "form_schema_version": 1,
    }
    assert prepare_update({"partner_user_fee_cents": None}, frozenset()).unset_fields == ()
    indexed_create = prepare_create({"fields": [{}, {}]}, "s", "n")
    assert [field["name"] for field in indexed_create.values["fields"]] == ["text_1", "text_2"]
    preserved = prepare_create({
        "fields": [], "required_fields": ["external"], "filter_tag": "tag",
        "required_uploads": ["CV"], "field_mappings": [{"source_step_order": 1}],
        "conditions": [{"operator": "empty"}], "translations": {"de": {"title": "Titel"}},
        "email_subject_enter": "Subject",
    }, "survey", "now")
    assert preserved.values["required_fields"] == ["external"]
    assert preserved.values["filter_tag"] == "tag"
    assert preserved.values["required_uploads"] == ["CV"]
    assert preserved.values["field_mappings"] == [{"source_step_order": 1}]
    assert preserved.values["conditions"] == [{"operator": "empty"}]
    assert preserved.values["translations"] == {"de": {"title": "Titel"}}
    assert preserved.values["email_subject_enter"] == "Subject"
    nonempty_update = prepare_update(
        {"fields": [{}, {}], "required_fields": ["external"], "partner_user_fee_cents": 100},
        frozenset({"fields", "required_fields", "partner_user_fee_cents"}),
    )
    assert [field["name"] for field in nonempty_update.values["fields"]] == ["text_1", "text_2"]
    assert nonempty_update.values["required_fields"] == ["external"]
    assert nonempty_update.unset_fields == ()
    fields_only = prepare_update({"fields": []}, frozenset({"fields"}))
    assert fields_only.values == {"fields": [], "form_schema_version": 1}


def test_recursive_condition_leaves_preserve_all_and_any_children() -> None:
    a, b = {"operator": "empty"}, {"operator": "not_empty"}
    assert list(condition_leaves({"all_of": [a, {"any_of": [b]}]})) == [a, b]


def test_relation_audit_reports_every_invalid_relation() -> None:
    steps = [
        {"order": 1, "title": "Source", "fields": [{"name": "choice", "field_type": "text"}]},
        {"order": 1, "title": "Broken", "fields": [{"name": "docs", "field_type": "multiupload", "options": [{"label": "CV"}]}],
         "required_fields": ["missing"], "required_uploads": ["License"],
         "conditions": [
             {"source_step_order": 9, "field": "x"},
             {"source_step_order": 1, "field": "unknown", "action": "redirect", "target_step_order": 8},
         ],
         "field_mappings": [
             {"source_step_order": 9, "source_field": "x", "target_field": "missing"},
             {"source_step_order": 1, "source_field": "unknown", "target_field": "docs"},
         ]},
    ]
    messages = [issue.text() for issue in relation_issues(steps)]
    assert messages == [
        "#0 Survey: Doppelte Step-Reihenfolge vorhanden",
        "#1 Broken: Requirement verweist auf unbekanntes Feld 'missing'",
        "#1 Broken: Upload-Requirement 'License' ist keine Dokumentoption",
        "#1 Broken: Condition verweist auf fehlenden Source-Step #9",
        "#1 Broken: Condition verweist auf unbekanntes Feld 'unknown' in Step #1",
        "#1 Broken: Redirect-Ziel #8 fehlt",
        "#1 Broken: Field-Mapping hat keine plausible Quelle",
        "#1 Broken: Field-Mapping hat kein plausibles Zielfeld",
        "#1 Broken: Field-Mapping hat keine plausible Quelle",
    ]


def test_relation_audit_accepts_valid_requirements_conditions_and_mappings() -> None:
    steps = [
        {"order": 1, "title": "Source", "fields": [
            {"name": "choice", "field_type": "text"},
            {"name": "docs", "field_type": "multiupload", "options": ["CV", {"value": "License"}]},
        ], "required_fields": ["choice"], "required_uploads": ["CV", "License"]},
        {"order": 2, "title": "Target", "fields": [{"name": "copy"}],
         "conditions": [{"source_step_order": 1, "field": "choice", "action": "redirect", "target_step_order": 1},
                        {"source_step_order": 1, "field": "status"}],
         "field_mappings": [{"source_step_order": 1, "source_field": "choice", "target_field": "copy"}]},
    ]
    assert relation_issues(steps) == ()


def test_relation_issue_defaults_and_label_only_upload_option() -> None:
    assert (_option_name("CV"), _option_name({"value": "License", "label": "ignored"}),
            _option_name({"label": "Passport"}), _option_name({})) == (
        "CV", "License", "Passport", "",
    )
    issues = relation_issues([{
        "fields": [{"name": "docs", "field_type": "multiupload", "options": [{"label": "CV"}]}],
        "required_uploads": ["missing"],
    }])
    assert [issue.text() for issue in issues] == [
        "#0 : Upload-Requirement 'missing' ist keine Dokumentoption",
    ]
