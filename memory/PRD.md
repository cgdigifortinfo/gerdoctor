# GERdoctor - Praktizieren in Deutschland

## Architecture
```
/app/backend/
  server.py        (952 lines - Routes + App setup)
  database.py      (DB connection)
  models.py        (Pydantic models)
  auth.py          (JWT, password, auth helpers)
  helpers.py       (Email, storage, audit, completion calc)
  server.py.backup (Pre-refactor backup)
```

## Steps (12 total, 3 with duration for % calc)
1-Persoenliche Daten, 2-Antragstellung Approbation, 3-Uebersicht Antragstellung (4w),
4-FaMed, 5-Gleichwertigkeitspruefung, 6-Uebersicht Gleichwertigkeit (3m),
7-Service Kenntnisprüfung, 8-Meilenstein Kenntnisprüfung (3m),
9-Service Weiterbildung, 10-Meilenstein Job finden,
11-Jobangebote (multiselection), 12-Du hast dich nun beworben!

## Data Fixes Applied (2026-04-18)
- Missing progress records for Steps 11+12 created for all users
- Gap fix: Steps 5+6 auto-completed for users who already passed Step 7
- Duplicate in_progress states fixed (max 1 per user)
- MultiPartnerSubmission model: added missing `data` field

## Test Coverage
- E2E Walkthrough: 15 tests (all 12 steps + admin/partner verification + cleanup)
- Partner linking: 13 tests
- Step completion: 16 tests

## Completed
- [x] All core features
- [x] Refactoring: server.py split into modules (2026-04-18)
- [x] DB data integrity fix + E2E walkthrough test (2026-04-18)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
