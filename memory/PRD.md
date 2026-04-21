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
- [x] 2026-04-21: **Partner-User Seeding + mehr Demo-Ärzte** — `seed_users_only.py` erweitert: (1) ensure_partner_users() erzeugt idempotent für jede Partner-Org ohne verlinkten User einen `role=partner`-Account (Email `partner@<slug>.de`, PW Partner123!, `linked_user_ids` aktualisiert) — **9 Partner-User nachgelegt** (IQB, MedAkademie, FIA Academy, PraxisConnect, FaMed, InterPers Jobs, MedJob24, PraxisConnect Jobs, IQB-Umlaut-Variante). Jetzt 0 Orphan-Partner. (2) **12 Demo-Ärzte** (statt 7) mit breiterem Progress-Spektrum: fresh → Stammdaten → mid-block → deep-block → almost-done → Jobangebote-selbst. Partner-Picks referenzieren echte Partner-IDs + schreiben `partner_submissions` → Partner-Dashboards zeigen jetzt Live-Submissions (z.B. FIA sieht Chen, MedJob24 sieht Kowalski).
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
