from slices.step_templates.domain import (
    admin_actor, instantiated_step, sanitize_template_config, step_source_config,
    template_document, template_update, template_view,
)

def test_sanitize_rejects_non_mapping_and_strips_instance_fields():
    assert sanitize_template_config(None) == {}
    assert sanitize_template_config({"_id": 1, "id": 2, "order": 3, "is_active": False,
                                     "created_at": "a", "updated_at": "b", "title": "T"}) == {"title": "T"}

def test_template_documents_updates_and_views_preserve_editable_values():
    assert template_document("N", None, {"order": 1, "x": 2}, "now") == {
        "name": "N", "description": "", "config": {"x": 2}, "created_at": "now"}
    assert template_document("N", "D", {}, "now")["description"] == "D"
    update = template_update({"name": None, "description": "D", "config": {"id": 1, "x": 2}}, "later")
    assert update == {"description": "D", "config": {"x": 2}, "updated_at": "later"}
    assert template_update({"name": "N"}, "now") == {"name": "N", "updated_at": "now"}
    assert template_view({"_id": 7}) == {"id": "7", "name": "", "description": "", "config": {}, "created_at": None}
    assert template_view({"_id": 7, "name": "N", "description": "D", "config": {"x": 1},
                          "created_at": "now"}) == {"id": "7", "name": "N", "description": "D",
                                                     "config": {"x": 1}, "created_at": "now"}

def test_step_source_and_instantiation_create_clean_new_instance():
    assert step_source_config({"_id": 1, "order": 2, "title": "T"}) == {"title": "T"}
    result = instantiated_step({"order": 99, "title": "T"}, "survey", 4, "now")
    assert result == {"title": "T", "survey_id": "survey", "order": 4, "is_active": True,
                      "is_deleted": False, "current_version": 1, "created_at": "now"}
    assert admin_actor({"_id": 3, "email": "a@b.de"}) == {"id": "3", "email": "a@b.de", "role": "admin"}
