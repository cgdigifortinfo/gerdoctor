from slices.survey_administration.domain import (
    default_survey_document, normalized_slug, survey_document, survey_update, survey_view,
)
from slices.survey_administration.models import SurveyDraft

def test_slug_and_documents_are_normalized_without_mutating_theme():
    assert normalized_slug(None) == "" and normalized_slug("  Medical Survey ") == "medical-survey"
    theme = {"color": "blue"}
    doc = survey_document(SurveyDraft("N", " My Survey ", "", "", False, True, theme), "now")
    assert doc == {"name": "N", "slug": "my-survey", "description": "", "audience": "",
                   "is_active": False, "is_default": True, "theme": theme,
                   "created_at": "now", "updated_at": "now"}
    assert doc["theme"] is not theme
    assert survey_document(SurveyDraft("N", "x", theme=None), "now")["theme"] == {}
    detailed = survey_document(SurveyDraft("Named", "slug", "Description", "Audience"), "later")
    assert detailed["description"] == "Description" and detailed["audience"] == "Audience"

def test_updates_filter_none_normalize_slug_and_copy_theme():
    theme = {"x": 1}
    updated = survey_update({"name": None, "slug": " New Name ", "theme": theme}, "now")
    assert updated == {
        "slug": "new-name", "theme": {"x": 1}, "updated_at": "now"}
    assert updated["theme"] is not theme
    assert survey_update({"name": "N"}, "now") == {"name": "N", "updated_at": "now"}

def test_view_has_complete_defaults_and_full_values():
    assert survey_view({"_id": 1}) == {"id": "1", "name": "", "slug": "", "description": "",
        "audience": "", "is_active": True, "is_default": False, "theme": {},
        "created_at": None, "updated_at": None}
    full = {"_id": 2, "name": "N", "slug": "s", "description": "D", "audience": "A",
            "is_active": False, "is_default": True, "theme": {"x": 1}, "created_at": "c", "updated_at": "u"}
    assert survey_view(full) == {"id": "2", **{k: v for k, v in full.items() if k != "_id"}}

def test_default_document_contains_stable_doctor_survey_contract():
    doc = default_survey_document("aerzte", "now")
    assert doc == {"name": "Ärzte Anerkennung", "slug": "aerzte",
        "description": "Anerkennungs- und Arbeitseinstiegsprozess fuer internationale Aerztinnen und Aerzte.",
        "audience": "Internationale Aerztinnen und Aerzte", "is_active": True, "is_default": True,
        "theme": {}, "created_at": "now", "updated_at": "now"}
