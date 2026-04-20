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
- [x] 2026-04-20: **Flowbuilder v2** — Palette-Sidebar mit 6 draggable Step-Typen (Formular, Entscheidung, Partner, Partner Multi, Meilenstein, Info). Drag&Drop auf Canvas öffnet Step-Dialog mit vorausgefülltem Typ. Edge-Drag von Source-Handle zu Target-Handle öffnet Condition-Modal (Action/Feld/Operator/Wert) und persistiert die Condition via `adminAPI.updateStep`. Action-Legende oben rechts (Ausblenden, Blockieren, Auto-Abschluss, Weiter, Weiterleiten)
- [x] 2026-04-20: **E2E-Flowbuilder-Test** (`/app/backend/tests/e2e_flowbuilder.py`) — 8/8 PASS mit frischem Test-Admin, deckt Node-Rendering (24 steps), View-Toggle, Palette, Palette-Drop, Node-Edit, Node-Create, Edge-Condition, Node-Delete ab. **Vollständiger Cleanup** verifiziert: Step-Count (24), IDs, Conditions wiederhergestellt, Test-User gelöscht
- [x] 2026-04-20: **Admin Steps-Flowbuilder v1** (reactflow 11.11.4)
- [x] 2026-04-20: **Bugfix Milestone-Auto-Complete** — jetzt basierend auf Upload-Step-Status
- [x] 2026-04-20: **Partner-Insights-Dashboard** + **Match-Score** + **Partner-Self-Service Tags-Editor**
- [x] 2026-04-20: **Partner-Matching-Empfehlung** in User-Steps
- [x] 2026-04-20: **P2 E2E Walkthrough** 3/3 PASS + **Repro-Test** Milestone
- [x] 2026-04-20: **Step Template Library** + **Landing-Page CMS Feature-Boxen** + **Anerkennungsstatus Auto-Skip**
- [x] 2026-04-20: **Survey v2 restructure** (24 steps, decision + hide/auto_complete/block)

## Backlog
- [ ] P2: Webhook-Integration für externe System-Benachrichtigungen
- [ ] P2: Wöchentliche Insights-E-Mail an Partner (Mailgun bereits integriert)
- [ ] P3: Flowbuilder — Condition per Click auf Edge bearbeiten (aktuell nur via Node-Dialog)
- [ ] P3: Flowbuilder — Journey Simulator (Node-Farbe zeigt Sichtbarkeit für simulierten User)
- [ ] P3: Auto-Layout Button (dagre oder elk) statt horizontal-by-order

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
