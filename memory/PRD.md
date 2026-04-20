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
- [x] 2026-04-20: **Partner-Insights-Dashboard** (KPI-Cards, Fachrichtung/Bundesland-BarCharts, 30-Tage-Timeline, Conversion-Funnel – alles ohne externe Chart-Libraries)
- [x] 2026-04-20: **Match-Score-Spalte** im PartnerDashboard (sortiert desc nach Default, Star-Badge wenn match > 0, basiert auf `scoreUserForPartner` mit Partner-Tags vs User Bundesland/Fachrichtung)
- [x] 2026-04-20: **Partner-Self-Service Tags-Editor** (Chip-Multiselect mit Datalist-Autocomplete, Schnellauswahl-Chips, `/api/partner/partner-data` endpoint - nur `description` + `tags`)
- [x] 2026-04-20: **Partner-Matching-Empfehlung** (Scoring fachrichtung_gewuenscht/praktiziert + Bundesland, Recommended-Badge + Sortierung in partner_selection & partner_multiselection)
- [x] 2026-04-20: **P2 E2E Walkthrough-Suite** (`/app/backend/tests/p2_walkthrough.py` — 3/3 PASS)
- [x] 2026-04-20: **CMSContentUpdate.section** Optional + **apply-template** upsert
- [x] 2026-04-20: **Step Template Library** (CRUD + save-from-step + apply-at-order)
- [x] 2026-04-20: **Landing-Page 3 Feature-Boxen via CMS** (6 neue Felder, DE + EN)
- [x] 2026-04-20: **Anerkennungsstatus Auto-Skip** (5 Status-Werte mappen auf fertige Blöcke)
- [x] 2026-04-20: **Survey v2 restructure** (24 steps, decision type, hide/auto_complete/block actions)
- [x] Earlier: i18n DE/EN, admin impersonation, partner m:n, cascade deletes, ConfirmDialog, tag autocomplete

## Backlog
- [ ] P2: Webhook-Integration für externe System-Benachrichtigungen
- [ ] P3: Insights `by_fachrichtung`/`by_bundesland` – 'Unbekannt' zu 'Nicht erfasst' umbenennen oder Users ohne Step-1-Daten herausfiltern
- [ ] P3: Insights `conversion_rate_pct` als Float mit einer Nachkommastelle

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
