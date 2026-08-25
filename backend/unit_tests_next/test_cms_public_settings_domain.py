from slices.cms_public_settings.domain import (
    MASKED_VALUE, admin_settings, cms_seed_update, cms_update_fields,
    editable_settings, normalize_cms_payload, public_settings,
)
from slices.cms_public_settings.models import CmsPayload


def test_normalization_handles_invalid_plain_and_nested_legacy_payloads():
    assert normalize_cms_payload(None, "bad") == CmsPayload({}, {})
    plain = normalize_cms_payload({"title": "T"}, {"en": {"title": "E"}})
    assert plain.response() == {"content": {"title": "T"}, "translations": {"en": {"title": "E"}}}
    source = {"content": {"content": {"title": "inner"}, "title": "middle"},
              "title": "outer", "section": "ignored", "translations": {"de": {"x": 1}}}
    nested = normalize_cms_payload(source, {"en": {"title": "English"}})
    assert nested.content == {"title": "outer"}
    assert nested.translations == {"de": {"x": 1}, "en": {"title": "English"}}
    assert "content" in source


def test_update_fields_only_writes_translations_when_explicitly_supplied():
    assert cms_update_fields("home", {"x": 1}, None, False, "now") == {
        "section": "home", "content": {"x": 1}, "updated_at": "now"}
    assert cms_update_fields("home", {}, {"en": {}}, True, "now")["translations"] == {"en": {}}


def test_settings_filters_mask_and_remove_only_configured_values():
    values = {"empty": "", "secret": "value", "none": None, "masked": MASKED_VALUE, "visible": 0}
    assert editable_settings(values) == {"empty": "", "secret": "value", "visible": 0}
    assert admin_settings(values, {"secret", "empty", "absent"})["secret"] == MASKED_VALUE
    assert admin_settings(values, {"secret", "empty"})["empty"] == ""
    assert public_settings(values, {"secret", "absent"}) == {
        "empty": "", "none": None, "masked": MASKED_VALUE, "visible": 0}


def test_seed_update_backfills_without_overwriting_and_repairs_legacy_shape():
    existing = {"content": {"kept": "custom"}, "translations": {"en": {"kept": "custom-en"}}}
    update = cms_seed_update(existing, {"kept": "default", "new": "value"},
                             {"kept": "default-en", "new": "value-en"})
    assert update == {"content": {"kept": "custom", "new": "value"},
                      "translations": {"en": {"kept": "custom-en", "new": "value-en"}}}
    assert cms_seed_update(update, update["content"], update["translations"]["en"]) == {}
    repaired = cms_seed_update({"content": {"content": {"a": 1}}, "translations": {"en": "bad"}}, {}, {})
    assert repaired == {"content": {"a": 1}, "translations": {"en": {}}}
    assert cms_seed_update({"content": {}, "translations": {}}, {}, None) == {}
