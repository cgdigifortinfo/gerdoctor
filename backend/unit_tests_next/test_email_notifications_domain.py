from __future__ import annotations

import pytest

from slices.email_notifications.domain import (
    NoEditableFields, NoValidRecipients, editable_fields, normalized_recipients,
    partner_deep_link, render_email, render_notification, replace_variables,
    template_sort_key,
)
from slices.email_notifications.models import MessageTemplate


TEMPLATE = MessageTemplate(
    "welcome", "user", "Hallo {{ name }}", "<p>{{name}} {{missing}}</p>",
    "Neu: {{name}}", "Text {{ name }}", "description",
)


def test_variables_render_known_values_and_clear_missing_or_empty_input():
    assert replace_variables("{{ name }} / {{missing}} / {{zero}}", {"name": "Ada", "zero": 0}) == "Ada /  / 0"
    assert replace_variables("", {}) == ""


def test_email_rendering_combines_layout_defaults_and_overrides():
    rendered = render_email(TEMPLATE, "<h1>{{app_url}}</h1>", "<footer>{{name}}</footer>",
                            {"name": "Ada", "app_url": "/app"})
    assert rendered.subject == "Hallo Ada"
    assert rendered.html == (
        '<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"/></head>\n'
        '<body style="margin:0;padding:0;background:#f8fafc;">\n'
        '  <div style="max-width:640px;margin:0 auto;background:#ffffff;">\n'
        '    <h1>/app</h1>\n    <p>Ada </p>\n    <footer>Ada</footer>\n'
        '  </div>\n</body>\n</html>'
    )
    overridden = render_email(TEMPLATE, "", "", {"name": "Ada"}, "Override {{name}}", "Body {{name}}")
    assert overridden.subject == "Override Ada"
    assert "Body Ada" in overridden.html


def test_notification_rendering_distinguishes_none_from_empty_override():
    default = render_notification(TEMPLATE, {"name": "Ada"})
    assert (default.title, default.body) == ("Neu: Ada", "Text Ada")
    overridden = render_notification(TEMPLATE, {"name": "Ada"}, "", "Body {{name}}")
    assert (overridden.title, overridden.body) == ("", "Body Ada")


def test_editable_fields_filters_payload_and_rejects_empty_selection():
    assert editable_fields({"subject": "x", "key": "forbidden"}) == {"subject": "x"}
    with pytest.raises(NoEditableFields):
        editable_fields({"key": "x"})


def test_recipients_are_validated_deduplicated_case_insensitively_and_stable():
    assert normalized_recipients(" Admin@Example.com ", ["admin@example.com", None, "bad", "user@example.com"]) == (
        "Admin@Example.com", "user@example.com",
    )
    with pytest.raises(NoValidRecipients):
        normalized_recipients(None, ["", "invalid"])


def test_template_order_and_partner_link_are_deterministic():
    assert template_sort_key(TEMPLATE) == (2, "welcome")
    assert template_sort_key(MessageTemplate("x", "custom", "", "")) == (99, "x")
    assert partner_deep_link("https://app.test/", "u1") == "https://app.test/partner-dashboard?openUser=u1"
    assert partner_deep_link("", "u1") == "/partner-dashboard?openUser=u1"
