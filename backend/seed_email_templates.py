"""
Email templates migration / seed.

Creates (or upserts) the baseline rows in the `email_templates` collection:

  • `header`                         — global HTML block prepended to every mail
  • `footer`                         — global HTML block appended to every mail
  • `partner_new_submission`         — sent to partner users when a user submits
                                        to them via partner_select/-multi
  • `user_awaiting_partner`          — confirmation to user after submit
                                        ("Your partner will reach out shortly")
  • `user_milestone_completed`       — sent to user when partner closes the milestone

Run:  cd /app/backend && python3 seed_email_templates.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_TEMPLATES = {
    # ------------------------------------------------------------------ categories
    # category drives the "which variables show up in the preview picker" behavior
    # on the frontend. Values: 'layout' (header/footer), 'partner', 'user',
    # 'step' (generic step enter/update/leave).
    # ------------------------------------------------------------------
    "header": {
        "category": "layout",
        "subject": "",  # unused for global blocks
        "body_html": """<div style="background:#114f55;padding:20px 24px;">
  <a href="{{app_url}}" style="color:#ffffff;font-size:22px;font-weight:700;text-decoration:none;letter-spacing:0.5px;">
    IHCA
  </a>
  <div style="color:#b8dfe3;font-size:13px;margin-top:4px;">international health connect association</div>
</div>
<div style="padding:24px;font-family:Arial,sans-serif;color:#0f172a;line-height:1.55;">""",
        "description": "Kopfzeile (Logo & Branding) — wird vor jeder Mail eingefügt",
    },
    "footer": {
        "category": "layout",
        "subject": "",
        "body_html": """</div>
<div style="background:#f1f5f9;padding:18px 24px;font-family:Arial,sans-serif;font-size:12px;color:#64748b;border-top:1px solid #cbd5e1;">
  <p style="margin:0 0 8px 0;">Mit freundlichen Grüßen,<br/><strong style="color:#114f55;">Ihr IHCA-Team</strong></p>
  <p style="margin:0;">
    <a href="{{app_url}}" style="color:#114f55;text-decoration:none;">ihca.de</a>
    · <a href="{{app_url}}/impressum" style="color:#64748b;">Impressum</a>
    · <a href="{{app_url}}/datenschutz" style="color:#64748b;">Datenschutz</a>
  </p>
</div>""",
        "description": "Fußzeile (Grußformel, Rechtslinks) — wird nach jeder Mail eingefügt",
    },
    "partner_new_submission": {
        "category": "partner",
        "subject": "Neue Anmeldung von {{user_name}} für {{partner_name}}",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Neue Anmeldung</h2>
<p>Hallo,</p>
<p>ein neuer Arzt hat sich bei <strong>{{partner_name}}</strong> für Ihren Service registriert und wartet auf Ihre Rückmeldung.</p>

<table cellpadding="8" cellspacing="0" style="border-collapse:collapse;margin:16px 0;background:#f8fafc;border-radius:4px;">
  <tr><td style="color:#64748b;">Name</td><td><strong>{{user_name}}</strong></td></tr>
  <tr><td style="color:#64748b;">E-Mail</td><td><a href="mailto:{{user_email}}" style="color:#114f55;">{{user_email}}</a></td></tr>
  <tr><td style="color:#64748b;">Fachrichtung</td><td>{{field_of_study}}</td></tr>
  <tr><td style="color:#64748b;">Bundesland</td><td>{{bundesland}}</td></tr>
</table>

<p style="margin:24px 0;">
  <a href="{{open_user_link}}"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Anmeldung im Dashboard öffnen
  </a>
</p>
<p style="color:#64748b;font-size:13px;">Klicken Sie auf den Button, um direkt zu den Details des Arztes zu springen — dort können Sie den Nachweis hochladen und den Meilenstein freischalten.</p>""",
        "description": "An Partner bei neuer User-Anmeldung (partner_select / partner_multiselect)",
    },
    "user_awaiting_partner": {
        "category": "user",
        "subject": "Ihre Anmeldung bei {{partner_name}} wurde versendet",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Vielen Dank, {{user_name}}!</h2>
<p>Ihre Anmeldung bei <strong>{{partner_name}}</strong> wurde erfolgreich übermittelt.</p>

<div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:14px 18px;margin:18px 0;border-radius:2px;">
  <strong style="color:#92400e;">Wie geht es weiter?</strong><br/>
  <span style="color:#78350f;">Der Partner prüft Ihre Anfrage und wird sich in Kürze bei Ihnen melden. Sobald Ihr Meilenstein bearbeitet wurde, erhalten Sie automatisch eine Bestätigungsmail.</span>
</div>

<p>Sie können den aktuellen Status jederzeit in Ihrem Dashboard einsehen:</p>
<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Zum Dashboard
  </a>
</p>""",
        "description": "An User nach Partner-Anmeldung (Wartezeit-Info)",
    },
    "user_milestone_completed": {
        "category": "user",
        "subject": "{{partner_name}} hat Ihren Meilenstein abgeschlossen",
        "body_html": """<h2 style="color:#059669;margin:0 0 16px 0;">Gute Nachrichten, {{user_name}}!</h2>
<p><strong>{{partner_name}}</strong> hat Ihren Meilenstein <em>"{{milestone_title}}"</em> für Sie abgeschlossen.</p>

<div style="background:#d1fae5;border-left:4px solid #059669;padding:14px 18px;margin:18px 0;border-radius:2px;">
  <strong style="color:#065f46;">Was bedeutet das?</strong><br/>
  <span style="color:#064e3b;">Sie können jetzt mit dem nächsten Schritt auf Ihrer Reise zur deutschen Approbation fortfahren. Der Fortschritt in Ihrem Dashboard wurde automatisch aktualisiert.</span>
</div>

<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Nächsten Schritt ansehen
  </a>
</p>""",
        "description": "An User wenn Partner den Meilenstein freischaltet",
    },
    "user_step_entered": {
        "category": "step",
        "subject": "Schritt gestartet: {{step_title}}",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Hallo {{user_name}},</h2>
<p>Sie haben den Schritt <strong>{{step_title}}</strong> auf Ihrer Reise zur deutschen Approbation begonnen.</p>

<div style="background:#e0f2fe;border-left:4px solid #0284c7;padding:14px 18px;margin:18px 0;border-radius:2px;">
  <strong style="color:#075985;">Schritt {{step_order}} von {{total_steps}}</strong><br/>
  <span style="color:#0c4a6e;">{{step_description}}</span>
</div>

<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Schritt im Dashboard öffnen
  </a>
</p>""",
        "description": "An User wenn ein Schritt neu gestartet wird (email_on_enter)",
    },
    "user_step_updated": {
        "category": "step",
        "subject": "Schritt aktualisiert: {{step_title}}",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Hallo {{user_name}},</h2>
<p>Ihr Fortschritt im Schritt <strong>{{step_title}}</strong> wurde aktualisiert.</p>
<p style="color:#64748b;font-size:14px;">Sie können jederzeit in Ihrem Dashboard weiter­machen oder bereits eingetragene Daten anpassen.</p>

<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Zum Dashboard
  </a>
</p>""",
        "description": "An User wenn ein Schritt bearbeitet wird (email_on_edit)",
    },
    "user_step_completed": {
        "category": "step",
        "subject": "Schritt abgeschlossen: {{step_title}}",
        "body_html": """<h2 style="color:#059669;margin:0 0 16px 0;">Glückwunsch, {{user_name}}!</h2>
<p>Sie haben den Schritt <strong>{{step_title}}</strong> erfolgreich abgeschlossen.</p>

<div style="background:#d1fae5;border-left:4px solid #059669;padding:14px 18px;margin:18px 0;border-radius:2px;">
  <strong style="color:#065f46;">Weiter geht's!</strong><br/>
  <span style="color:#064e3b;">Schauen Sie in Ihrem Dashboard nach, welcher Schritt als Nächstes auf Sie wartet.</span>
</div>

<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Nächsten Schritt ansehen
  </a>
</p>""",
        "description": "An User wenn ein Schritt abgeschlossen wird (email_on_leave)",
    },
    "user_next_step_unlocked": {
        "category": "step",
        "subject": "Nächster Schritt freigeschaltet: {{step_title}}",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Weiter geht's, {{user_name}}!</h2>
<p>{{partner_name}} hat Ihren vorherigen Meilenstein abgeschlossen — Ihr nächster Schritt <strong>{{step_title}}</strong> ist jetzt für Sie freigeschaltet.</p>

<div style="background:#e0f2fe;border-left:4px solid #0284c7;padding:14px 18px;margin:18px 0;border-radius:2px;">
  <strong style="color:#075985;">Was kommt jetzt?</strong><br/>
  <span style="color:#0c4a6e;">{{step_description}}</span>
</div>

<p style="margin:20px 0;">
  <a href="{{app_url}}/dashboard"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Zum Dashboard
  </a>
</p>""",
        "description": "An User wenn Partner einen Meilenstein abschließt und dadurch der nächste Schritt freigegeben wird",
    },
    "user_password_reset": {
        "category": "user",
        "subject": "Passwort zurücksetzen — IHCA",
        "body_html": """<h2 style="color:#114f55;margin:0 0 16px 0;">Passwort zurücksetzen</h2>
<p>Hallo,</p>
<p>Sie (oder jemand in Ihrem Namen) hat angefordert, das Passwort Ihres IHCA-Kontos zurückzusetzen.</p>

<p style="margin:24px 0;">
  <a href="{{reset_link}}"
     style="background:#114f55;color:#ffffff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block;">
    Passwort jetzt zurücksetzen
  </a>
</p>

<p style="color:#64748b;font-size:13px;">Dieser Link ist <strong>1 Stunde</strong> gültig. Sollten Sie keine Zurücksetzung angefordert haben, können Sie diese E-Mail einfach ignorieren.</p>""",
        "description": "Passwort-Reset-Link per E-Mail",
    },
}


async def run() -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    created, updated = 0, 0
    for key, tpl in DEFAULT_TEMPLATES.items():
        existing = await db.email_templates.find_one({"key": key})
        doc = {
            "key": key,
            "category": tpl.get("category", "user"),
            "subject": tpl["subject"],
            "body_html": tpl["body_html"],
            "description": tpl["description"],
            "updated_at": now_iso(),
        }
        if existing:
            # Don't overwrite user-edited templates; only fill missing fields
            fields_to_set = {k: v for k, v in doc.items()
                             if k != "key" and (k not in existing or existing.get(k) in (None, ""))}
            if fields_to_set:
                await db.email_templates.update_one({"key": key}, {"$set": fields_to_set})
                updated += 1
        else:
            doc["created_at"] = now_iso()
            await db.email_templates.insert_one(doc)
            created += 1
    print(f"  ✓ email_templates: {created} created, {updated} updated, "
          f"{len(DEFAULT_TEMPLATES) - created - updated} untouched")
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
