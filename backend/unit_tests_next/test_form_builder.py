"""Use-case tests for canonical form normalization and migration."""

from copy import deepcopy

import pytest

from slices.step_configuration.form_builder import (
    FORM_SCHEMA_VERSION,
    migrate_snapshot_form_configs,
    normalize_step_document,
    normalize_step_field,
)


class TestNormalizeStepField:
    def test_normalizes_legacy_choice_without_losing_custom_metadata(self):
        source = {
            "label": "Gewünschte Fachrichtung",
            "field_type": "SELECTBOX",
            "options": [{"value": "innere", "label": "Innere", "score": 3}],
            "custom_plugin": "legacy",
        }
        result = normalize_step_field(source)
        assert result["name"] == "gew_nschte_fachrichtung"
        assert result["field_type"] == "selectbox"
        assert result["options"][0]["score"] == 3
        assert result["custom_plugin"] == "legacy"
        assert source["field_type"] == "SELECTBOX"

    def test_unknown_field_type_safely_falls_back_to_text(self):
        result = normalize_step_field({"field_type": "executable", "label": "Code"}, 2)
        assert result["field_type"] == "text"
        assert result["name"] == "code"

    @pytest.mark.parametrize("raw,expected", [(None, 4), (1, 2), (8, 8), (99, 20)])
    def test_textarea_rows_are_clamped(self, raw, expected):
        assert normalize_step_field({"field_type": "textarea", "rows": raw})["rows"] == expected

    def test_invalid_textarea_rows_use_default_instead_of_crashing_migration(self):
        assert normalize_step_field({"field_type": "textarea", "rows": "invalid"})["rows"] == 4

    @pytest.mark.parametrize("raw,expected", [(None, 2), (1, 2), (3, 3), (9, 4)])
    def test_heading_level_is_clamped(self, raw, expected):
        assert normalize_step_field({"field_type": "heading", "heading_level": raw})["heading_level"] == expected

    def test_invalid_heading_level_uses_default_instead_of_crashing_migration(self):
        assert normalize_step_field({"field_type": "heading", "heading_level": "invalid"})["heading_level"] == 2

    def test_content_fields_can_never_be_required(self):
        assert normalize_step_field({"field_type": "paragraph", "required": True})["required"] is False

    def test_upload_defaults_are_safe(self):
        result = normalize_step_field({"field_type": "multiupload"})
        assert result["multiple"] is True
        assert ".pdf" in result["accept"]
        assert result["options"] == []


class TestFormMigration:
    def test_document_normalization_is_idempotent_and_non_mutating(self):
        source = {"title": "Step", "fields": [{"label": "E-Mail", "field_type": "email"}]}
        original = deepcopy(source)
        once = normalize_step_document(source)
        twice = normalize_step_document(once)
        assert once == twice
        assert source == original
        assert once["form_schema_version"] == FORM_SCHEMA_VERSION

    def test_snapshot_migration_preserves_unrelated_collections(self):
        snapshot = {
            "version": 4,
            "collections": {
                "steps": [{"fields": [{"label": "Name"}]}],
                "partners": [{"name": "Partner"}],
            },
        }
        migrated = migrate_snapshot_form_configs(snapshot)
        assert migrated["collections"]["partners"] == snapshot["collections"]["partners"]
        assert migrated["collections"]["steps"][0]["form_schema_version"] == FORM_SCHEMA_VERSION
        assert "form_schema_version" not in snapshot["collections"]["steps"][0]

    def test_snapshot_without_collections_gets_an_attached_collection_map(self):
        migrated = migrate_snapshot_form_configs({"version": 1})
        assert migrated["collections"] == {"steps": []}

