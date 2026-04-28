# GERdoctor - Praktizieren in Deutschland

## Architecture
```
/app/backend/
  server.py, database.py, models.py, auth.py, helpers.py
  seed_survey_v2.py (24-step survey seeder, resets progress on run)
  tests/  (4+ suites incl. test_survey_v2.py)
/app/frontend/src/
  pages/  (Landing, Auth, UserDashboard, PartnerDashboard, AdminDashboard)
  lib/    (api.js, stepVisibility.js)
```

## Survey v2 - Step Engine (2026-04-20)
24 seeded steps covering 7 themes. Each theme (except Jobangebote) follows the pattern:
`decision -> upload | partner_selection -> milestone`

### Step Order
| # | Title | Type | Notes |
|---|-------|------|-------|
| 1 | Persönliche Daten | form | Stammdaten incl. date_of_birth, Anerkennungsstatus (7), Bundesland (16), Fachrichtung praktiziert/gewünscht (35 each) |
| 2 | Antragstellung Approbation | decision | Upload vs Partner |
| 3 | Dokumente Antragstellung Approbation | form | hide if decision(2)!=upload |
| 4 | Service Antragstellung Approbation | partner_selection | hide if decision(2)!=partner |
| 5 | Übersicht Antragstellung Approbation | milestone | auto_complete if decision(2)==upload |
| 6-9 | Fachsprachenprüfung block | same pattern | block(5) until Antragstellung milestone completed; tag=Fachsprachenprüfung |
| 10-13 | Gleichwertigkeitsprüfung block | same | tag=Gleichwertigkeitsprüfung |
| 14-17 | Kenntnisprüfung block | same | tag=Kenntnisprüfung |
| 18-20 | Jobangebote | decision(selbst/partner_nutzen) + multi partner + milestone | no upload step |
| 21-24 | Weiterbildung block | same | tag=Weiterbildung |

### Condition Actions (Step.conditions[*].action)
- `block` — step is locked (lock icon)
- `hide`  — step is completely hidden + excluded from progress/ETA
- `auto_complete` — step auto-completes when condition met (triggered server-side on every progress update)
- `allow_next` / `redirect` — pre-existing actions

### New Step Type
- `decision` — renders the fields[0].options as 2 clickable cards; clicking saves `data.decision=value` and marks step completed

## i18n System
- UI strings: LanguageContext.js (150+ keys)
- Steps + CMS: `translations` field per record, Admin UI has DE/EN tabs
- Frontend `localize(item, field)` helper

## Completed (recent)
- [x] 2026-04-27: **Email-Domain-Migration → @chrizz1001.de** — alle User-Emails außer dem Master-Admin (`admin@example.com`) auf `<local>@chrizz1001.de` migriert. 108 User-Konten (94 + 14 mit Suffix-Konflikt-Auflösung), 13 Partner-`contact_email`s, 28 `partner_submissions.user_email`-Felder. Idempotente Migration `migrate_emails_to_chrizz.py` mit deterministischem Slug-Suffix für `partner@*`-Konflikte (z.B. `partner@example.com` → `partner-example@chrizz1001.de`). Seed-Files (`seed_users_only.py`, `seed_survey_v2.py`, `seed_migration*.py`) und 9 Test-Files synced. Frontend-Placeholder + EmailTemplateEditor-Dummy aktualisiert. test_credentials.md komplett neu geschrieben. Tests: 41/41 PASS, Logins für admin/partner/user verifiziert.
- [x] 2026-04-27: **Rebrand GERdoctor → IHCA** — vollständige Umbenennung in Frontend, Backend, Mail-Templates, Logo (`IHCA` + Tagline „international health connect association"), CMS-Hero-Title, Settings-Defaults, MIME-Type für FlowBuilder-Drag&Drop. Idempotente Migration `migrate_rebrand_ihca.py` rewrote 13 User-Emails (`*@gerdoctor.de` → `*@ihca.de`), patchte site_settings (Logo-Parts) und CMS-Content. Backend-Tests (Email-Templates, UI-Flags, Milestone-Hide) passen 41/41. Test-Credentials in `/app/memory/test_credentials.md` aktualisiert.

## Completed (recent)
- [x] 2026-04-21: **Step-Flow Milestone-Visibility Fix** — Milestone-Steps (5, 9, 13, 17, 20, 24) waren fälschlicherweise im Timeline sichtbar, bevor der User am Entscheidungsfeld (2/6/10/14/18/21) gewählt hatte. Nach Partner-Milestone-Completion sah der User statt des erwarteten Entscheidungsfeldes direkt die nächste Milestone. **Fix (3 Teile)**:
  1. `seed_survey_v2.py` um `hide`-Condition `{field: 'decision', operator: 'empty', source_step_order: decision_order}` auf jeden Milestone-Step erweitert.
  2. `_evaluate_condition` (Backend + Frontend `stepVisibility.js`): wenn `field` explizit gesetzt ist, aber nicht in `data` vorhanden, Rückgabe `undefined` statt Fallback auf `status` — damit `empty`-Operator korrekt auf fehlende Data-Felder reagiert (vorher: `status='in_progress'` war nie empty → Milestone blieb sichtbar).
  3. `migrate_milestone_hide_when_decision_empty.py` für bestehende DB-Einträge (idempotent, 6 Steps aktualisiert).
  Test-Status: 13 neue Pytest-Cases in `test_milestone_hide_flow.py` (darunter parametrisierte Tests für alle 6 Blöcke, Partner-Completion-Reproduction, Multi-Partner Jobangebote, Evaluator-Direktprüfung) + alle 24 Email-Template-Tests als Regression — **37/37 PASS**.
- [x] 2026-04-21: **E-Mail-Template-Editor + Partner-Deep-Linking** — neue MongoDB-Collection `email_templates` mit 10 deutschsprachigen Default-Vorlagen (Header/Footer/partner_new_submission/user_awaiting_partner/user_milestone_completed/user_next_step_unlocked/user_step_entered/user_step_updated/user_step_completed/user_password_reset). Admin-Tab „E-Mail-Vorlagen" mit WYSIWYG-Editor (`react-simple-wysiwyg`), HTML-Code-Toggle, Variablen-Chips (Klick = Clipboard), Live-Vorschau via `/api/admin/email-templates/{key}/preview` mit **User & Step-Pickern** und Header+Body+Footer-Wrap im iframe. CRUD: `GET /api/admin/email-templates`, `GET|PUT /api/admin/email-templates/{key}`, `POST /api/admin/email-templates/{key}/reset`, `POST /api/admin/email-templates/{key}/preview`. Startup-Seed ist idempotent (überschreibt keine Admin-Edits). **Alle Mail-Trigger migriert** (Passwort-Reset, Step-Enter/Edit/Leave, Partner-Neue-Anmeldung, User-Wartet-auf-Partner, User-Meilenstein-abgeschlossen, Nächster-Step-freigeschaltet) laufen jetzt zentral über `render_email(key, vars)` (wraps Header+Footer, substituiert `{{variable}}`-Tokens inkl. `{{app_url}}` und `{{open_user_link}}`). Partner-Dashboard liest `?openUser=<user_id>`, öffnet automatisch den User-Modal, wechselt auf den passenden Tab (my-users/completed-users/other-users) und bereinigt die URL per `history.replaceState`. Invalid IDs → deutscher Error-Toast. **Test-Status**: Backend 13/13 pytest PASS (test_email_templates_iter35.py), Frontend E2E 100% (Iter-36 Re-Test — Deep-Link valid+invalid, Clipboard, Editor-Tab).
- [x] 2026-04-21: **Partner-E-Mail-Benachrichtigung bei Buchung** — neuer Helper `notify_partner_of_new_submission(partner, user, data)` in `helpers.py`. Wird automatisch nach `/api/partners/submit` (single) und `/api/partners/submit-multi` (multi) gefeuert — nur bei NEUEN Submissions (nicht bei Updates), damit kein Spam entsteht. Sendet an: (1) `partner.contact_email`, (2) alle `role=partner` User mit `partner_id=X`, (3) `linked_user_ids`. Dedupliziert + respektiert `notification_prefs.email=false` (Opt-out). HTML-Body enthält User-Name, E-Mail, Fachrichtung, Bundesland, Step-Order, Partner-Name. Mail-Fehler blockieren die Submission nicht. **Regression-Test** `test_partner_submission_notification.py`: 3/3 Cases (Recipients, Body-Inhalt, Opt-Out) PASS.
- [x] 2026-04-21: **Anmeldungen-Spalte erweitert + Seed mit realistischer Partner-Backlog** — Admin Users zeigt für alle Rollen, Admin Partners hat eigene Spalte, Seed hinterlässt 10 Partner mit je 1 User wartend. Kombinatorik-Test deckt alle 6 partner_selection/multi-Steps ab.
- [x] 2026-04-21: **Re-open-Button + Abgeschlossen-am Spalte** in Partner Completed-Users-Tab.
- [x] 2026-04-21: **Feature: "Completed Users" Tab im PartnerDashboard** — automatisches Split basierend auf `partner_work_completed` Boolean pro Submission.
- [x] 2026-04-21: **Bugfix: Partner sieht User nicht nach Partner-Wahl** — Duplikate IQB-Partner-Orgs (Umlaut vs no-Umlaut) gemergt via `merge_duplicate_iqb_partners.py`.
- [x] 2026-04-21: **Partner-User Seeding + mehr Demo-Ärzte** — 9 Partner-User nachgelegt, 12 Demo-Ärzte mit breiterem Progress-Spektrum, Partner-Dashboards sehen Live-Submissions.
- [x] 2026-04-21: **Header: Fortschritt-Prozentsatz neben Abschlussdatum** — UserDashboard-Header zeigt zwei Pills (ETA + Progress-Bar mit %).
- [x] 2026-04-21: **Upload-Step erzwingt Datei-Nachweis** — Frontend-Button "Complete" ist disabled mit Label "Upload erforderlich" bis mindestens eine Datei im Multiupload-Feld hochgeladen ist. Backend `/api/steps/progress` lehnt empty-Data-Completions auf Steps mit `multiupload + required=true` Feldern mit HTTP 400 + deutscher Message ab ("Mindestens ein Dokument für 'Dokumente' ist erforderlich."). Schließt die Lücke zum Milestone-Block komplett.
- [x] 2026-04-21: **Bugfix: Milestone blockiert wenn Upload-Pfad ohne Datei** — Milestone `auto_complete` umgestellt auf `has_upload(documents)`, zusätzliche `block`-Condition mit `all_of: [decision=upload, missing_upload]`. `_evaluate_condition` unterstützt jetzt `all_of`/`any_of`. Migration `migrate_milestone_conditions.py` aktualisiert 5 Milestones + rollt 2 spurious Auto-Completions zurück.
- [x] 2026-04-21: **Admin User-Liste zeigt Partner-Namen** — neue "Partner"-Spalte aggregiert aus partner_id + linked_user_ids + selected_partner in progress.data.
- [x] 2026-04-21: **Partner kann Milestone freischalten inkl. Datei-Upload** — Backend `/api/partner/users/{id}` liefert neue Liste `partner_managed_step_ids` (alle partner_selection-Steps wo User diesen Partner gewählt hat + zugehöriger nächster Milestone-Step im gleichen Block). PartnerDashboard Modal: Milestones die zum Partner gehören zeigen eigenen "Meilenstein abschließen"-Block mit File-Input + "Hochladen & Abschließen"-Button. Hochgeladene Dateien landen in `data.partner_uploads[]` (cumulative). Bereits bestehende Uploads werden unter "Partner-Nachweise" aufgelistet. Regression test `test_partner_milestone_complete.py` PASS (4/4 Checks + Cleanup).
- [x] 2026-04-20: **Animierter Journey-Durchlauf** — Play-Button im Flowbuilder startet Step-by-Step-Walkthrough (1.5s/Step). Aktueller Step pulsiert in Amber, Overlay unten zeigt `Step X / Y` + kumulative ETA (Tage/Wochen/Monate). Respektiert aktives Simulator-Profil. E2E Case 15 PASS.
- [x] 2026-04-20: **User-Only Re-Seed** (`seed_users_only.py`) — löscht nur `role='user'` + deren Progress/Submissions/Uploads, legt 7 Demo-Ärzte neu an. Admins, Partner-User, Partner-Orgs, Steps, CMS bleiben unverändert. Konflikt-Schutz: Emails die bereits von Partner-Usern (z.B. `dr.schmidt@gerdoctor.de`) belegt sind, werden übersprungen.
- [x] 2026-04-20: **test_survey_v2.py Fix** — 2 veraltete Auto-Complete-Assertions an aktuellen Milestone-Bugfix angepasst (Upload-Step #3 status_is completed statt Decision=upload). 12/12 PASS.
- [x] 2026-04-20: **Journey Simulator + Undo/Redo History** — Toolbar-Dropdown mit 4 Profilen (Frisch, Upload-Pfad, Partner-Pfad, Approbiert) tint Nodes live (sichtbar/versteckt/blockiert/auto-abgeschlossen). Undo/Redo-Stack für Node-Positionen (Auto-Layout + Drag), Toolbar-Buttons + Keyboard-Shortcuts (Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y). Logik in `hooks/useFlowHistory.js` + `components/FlowSimulatorPanel.js` ausgelagert.
- [x] 2026-04-20: **Flowbuilder Linear-Layout** — neuer Algorithmus respektiert `step.order` streng. Aufeinanderfolgende Steps mit `hide`-Conditions auf dieselbe Decision werden als **parallele Lanes** (vertikal gestapelt) bei gleicher X-Position gerendert, alle anderen Steps seriell auf der Mittelachse. Ersetzt dagre als Default-Layout — dagre bleibt als interner Fallback
- [x] 2026-04-20: **Fullscreen-Modus** — Browser Fullscreen API (kein Library-Dependency), Toggle-Button oben links, Node-Layout dehnt sich auf `h-screen w-screen`. `fullscreenchange`-Event-Listener synchronisiert Icon (ArrowsOut ↔ ArrowsIn)
- [x] 2026-04-20: **E2E Flowbuilder Tests 12/12 PASS** — erweitert um Case 11 (Fullscreen-Trigger) + Case 12 (parallele Lanes: upload+partner haben gleiches X, unterschiedliches Y), vollständiger Cleanup
- [x] 2026-04-20: **Flowbuilder Condition-Edit via Edge-Click** + **Auto-Layout + Global Persistence** (`steps.flow_position` + `PUT /api/admin/steps/layout-bulk`)
- [x] 2026-04-20: **Flowbuilder Palette + Edge-Drag**
- [x] 2026-04-20: **Bugfix Milestone-Auto-Complete** (status_is auf Upload-Step)
- [x] 2026-04-20: **Partner-Insights-Dashboard** + **Match-Score** + **Partner-Self-Service Tags-Editor**
- [x] 2026-04-20: **Partner-Matching-Empfehlung** in User-Steps
- [x] 2026-04-20: **Step Template Library** + **Landing-Page CMS Feature-Boxen** + **Anerkennungsstatus Auto-Skip**
- [x] 2026-04-20: **Survey v2 restructure** (24 steps, decision + hide/auto_complete/block)

## Backlog
- [ ] P1: Bulk Import/Export für Step-Konfigurationen (JSON)
- [ ] P2: Webhook-Integration für externe System-Benachrichtigungen
- [ ] P2: Wöchentliche Insights-E-Mail an Partner (Mailgun bereits integriert)

## Known Warnings
- None blocking. Two console errors observed on load (non-blocking, non-React-loop).

## Key API Endpoints (v2)
- `GET /api/steps` - list (respects is_active)
- `GET /api/steps/visibility` - returns `{hidden_step_ids, blocked_step_ids}` for current user
- `GET /api/steps/progress` - user progress
- `PUT /api/steps/progress` - triggers `apply_auto_completes` afterwards; if step_id==Stammdaten and data.anerkennungsstatus is set, triggers `apply_anerkennungsstatus_skips`
- `PUT /api/admin/users/{id}/progress` - also triggers auto-complete + anerkennungsstatus skips
- `PUT /api/partner/users/{id}/progress` - triggers auto-complete
- `GET|POST|PUT|DELETE /api/admin/step-templates[/<id>]` - Template CRUD
- `POST /api/admin/step-templates/from-step/{step_id}?name=X&description=Y` - save existing step as template
- `POST /api/admin/step-templates/{id}/apply?order=N` - instantiate template as new step at order N (shifts others)
- `GET /api/cms/home` - now includes `box1_title`, `box1_description`, `box2_*`, `box3_*` content + EN translations

## Anerkennungsstatus → Block Auto-Skip Map
| Anerkennungsstatus | Blocks automatisch erledigt |
|--------------------|-----------------------------|
| Fachsprachenprüfung Medizin ist geplant | — |
| Fachsprachenprüfung Medizin bestanden | Fachsprachenprüfung |
| Berufserlaubnis beantragt | — (User kommt normal durch Antragstellung) |
| Berufserlaubnis erteilt | Antragstellung Approbation |
| Termin Kenntnisprüfung beantragt | Antragstellung + Fachsprachen |
| Gleichwertigkeitsprüfung beantragt | Antragstellung + Fachsprachen |
| In Deutschland approbiert | Antragstellung + Fachsprachen + Gleichwert. + Kenntnisprüfung |
