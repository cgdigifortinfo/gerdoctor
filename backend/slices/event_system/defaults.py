"""Canonical event types and their initial handlers."""
from __future__ import annotations

from typing import Any

DEFAULT_EVENT_CONFIGS: dict[str, dict[str, Any]] = {
    "partner.step.completed": {
        "label": "Partner schließt Step ab",
        "description": "Wird ausgelöst, wenn ein Partner einen verwalteten Step für einen User abschließt.",
        "enabled": True,
        "handlers": [
            {"id": "notify-user-email", "type": "email", "label": "User per E-Mail informieren",
             "enabled": True, "recipient": "user", "template_key": "user_milestone_completed"},
            {"id": "notify-user-browser-app", "type": "notification", "label": "Browser/App Notification",
             "enabled": False, "recipient": "user", "template_key": "user_milestone_completed",
             "channels": ["browser", "app"], "provider": "unconfigured"},
        ],
    },
    "partner.step.rejected": {
        "label": "Partner lehnt Step ab",
        "description": "Setzt den User einen sichtbaren Schritt zurück und informiert ihn über den Grund.",
        "enabled": True,
        "handlers": [
            {"id": "notify-user-email", "type": "email", "label": "User per E-Mail informieren",
             "enabled": True, "recipient": "user", "template_key": "user_partner_step_rejected"},
            {"id": "notify-user-browser-app", "type": "notification", "label": "Browser/App Notification",
             "enabled": False, "recipient": "user", "template_key": "user_partner_step_rejected",
             "channels": ["browser", "app"], "provider": "unconfigured"},
        ],
    },
    "partner.document.uploaded": {
        "label": "Partner lädt Dokument hoch",
        "description": "Protokolliert Nachweise, die ein Partner im User-Step hinterlegt.",
        "enabled": True, "handlers": [],
    },
}
