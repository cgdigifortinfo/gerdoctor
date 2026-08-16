"""Form-builder schema and legacy-field migration regression coverage."""

try:
    from backend.form_builder import (
        FORM_SCHEMA_VERSION,
        migrate_snapshot_form_configs,
        normalize_step_document,
        normalize_step_field,
    )
    from backend.models import StepCreate
except ModuleNotFoundError:  # container test runs use /app/backend as cwd
    from form_builder import (
        FORM_SCHEMA_VERSION,
        migrate_snapshot_form_configs,
        normalize_step_document,
        normalize_step_field,
    )
    from models import StepCreate


def test_legacy_field_gets_stable_builder_defaults():
    field = normalize_step_field({
        "name": "first_name",
        "field_type": "text",
        "label": "Vorname",
        "required": True,
    })

    assert field == {
        "name": "first_name",
        "field_type": "text",
        "label": "Vorname",
        "required": True,
        "id": "first_name",
        "width": "full",
        "help_text": "",
    }


def test_decision_option_metadata_is_preserved():
    option = {
        "value": "fastlane",
        "label": "Überholspur",
        "primary": True,
        "info_title": "Direkter Einstieg",
        "info_body": "<p>Information</p>",
    }
    field = normalize_step_field({
        "name": "decision",
        "field_type": "decision",
        "label": "Wie möchten Sie fortfahren?",
        "options": [option],
    })

    assert field["options"] == [option]
    assert field["options"][0]["primary"] is True


def test_content_fields_are_never_required():
    field = normalize_step_field({
        "name": "intro",
        "field_type": "html",
        "label": "Einleitung",
        "content": "<p>Willkommen</p>",
        "required": True,
    })

    assert field["required"] is False
    assert field["content"] == "<p>Willkommen</p>"


def test_snapshot_steps_are_migrated_without_mutating_source():
    snapshot = {"collections": {"steps": [{"title": "Alt", "fields": [{"name": "notes", "field_type": "textarea", "label": "Notizen"}]}]}}

    migrated = migrate_snapshot_form_configs(snapshot)

    assert "form_schema_version" not in snapshot["collections"]["steps"][0]
    step = migrated["collections"]["steps"][0]
    assert step["form_schema_version"] == FORM_SCHEMA_VERSION
    assert step["fields"][0]["rows"] == 4


def test_api_schema_keeps_rich_builder_configuration():
    step = StepCreate.model_validate({
        "title": "Builder",
        "description": "Test",
        "order": 99,
        "step_type": "form",
        "fields": [{
            "id": "hero",
            "name": "hero",
            "field_type": "image",
            "label": "Titelbild",
            "image_url": "https://example.com/hero.jpg",
            "alt_text": "Beispiel",
            "caption": "Bildunterschrift",
            "width": "half",
        }, {
            "id": "bio",
            "name": "bio",
            "field_type": "textarea",
            "label": "Biografie",
            "help_text": "Kurzer Überblick",
            "rows": 8,
            "min_length": 20,
            "max_length": 500,
        }],
    })

    payload = step.model_dump(exclude_none=True)
    assert payload["fields"][0]["caption"] == "Bildunterschrift"
    assert payload["fields"][0]["width"] == "half"
    assert payload["fields"][1]["rows"] == 8
    assert normalize_step_document(payload)["form_schema_version"] == FORM_SCHEMA_VERSION
