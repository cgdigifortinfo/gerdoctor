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
- [x] 2026-04-20: **Partner-Matching-Empfehlung** (Scoring nach fachrichtung_gewuenscht/praktiziert + Bundesland aus Step 1, Recommended-Badge + Sortierung in partner_selection & partner_multiselection, Praxis-Partner um Jobangebote-Tag + Bundesland-Tags erweitert)
- [x] 2026-04-20: **P2 E2E Walkthrough-Suite** (`/app/backend/tests/p2_walkthrough.py` — Jobangebote Selbst/Partner + PartnerDashboard hide filter, 3/3 PASS, API+UI verifiziert)
- [x] 2026-04-20: **Nice-to-haves** – `CMSContentUpdate.section` jetzt Optional, `apply-template` via `update_one(upsert=True)` statt `insert_many` (idempotent)
- [x] 2026-04-20: **Step Template Library** (save-step-as-template, list/apply/delete, new MongoDB `step_templates` collection, Admin UI panel in Steps tab)
- [x] 2026-04-20: **Landing-Page 3 Feature-Boxen via CMS** (6 neue Felder in `cms_content.home`, DE + EN Translations, Admin-CMS-Editor erweitert, Backfill für bestehende Installationen)
- [x] 2026-04-20: **Anerkennungsstatus Auto-Skip** (5 Status-Werte mappen auf bereits-fertige Themenblöcke, `apply_anerkennungsstatus_skips` in helpers.py, Trigger bei User- und Admin-Progress-Update)
- [x] 2026-04-20: **Survey v2 restructure** (24 steps, 3 new condition actions, 1 new step_type, PartnerDashboard hide-filter, demo-data reseed)
- [x] 2026-04-20: Backend helpers refactor (_get_step_context, apply_auto_completes)
- [x] 2026-04-20: Fixed "Maximum update depth" infinite re-render in UserDashboard via useMemo on visibleSteps
- [x] 2026-04-20: Deduplicated data-testid on decision-options (desktop vs mobile scope)
- [x] Earlier: i18n DE/EN for Steps + CMS, admin impersonation, partner m:n linking, cascade deletes, ConfirmDialog, tag autocomplete

## Backlog
- [ ] P2: Webhook-Integration für externe System-Benachrichtigungen
- [ ] P3: Partner können via eigene UI Bundesland/Fachrichtung-Tags pflegen (aktuell nur via Admin Tag-Multiselect)
- [ ] P3: Recommendation-Score auch in PartnerDashboard-Matching-Ansicht zeigen

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
