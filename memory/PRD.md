# GERdoctor - Praktizieren in Deutschland

## Architecture
```
/app/backend/
  server.py        (952 lines - Routes + App setup)
  database.py      (7 lines - MongoDB connection)
  models.py        (183 lines - Pydantic models)
  auth.py          (71 lines - JWT, password, auth helpers)
  helpers.py       (181 lines - Email, storage, audit, completion calc)
  server.py.backup (2151 lines - Pre-refactor backup)
/app/frontend/
  React + Tailwind + Shadcn/UI
```
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Steps (12 total)
1. Persoenliche Daten (form)
2. Antragstellung Approbation (partner_selection, tag=Antragstellung)
3. Uebersicht Antragstellung Approbation (milestone, 4 weeks)
4. FaMed (display, link to famed-test.de)
5. Gleichwertigkeitspruefung (partner_selection, tag=Gleichwertigkeitspruefung)
6. Uebersicht Gleichwertigkeitspruefung (milestone, 3 months)
7. Service Kenntnisprüfung (partner_selection, tag=Kenntnisprüfung)
8. Meilenstein Kenntnisprüfung (milestone, 3 months)
9. Service Weiterbildung (partner_selection, tag=Weiterbildung)
10. Meilenstein Job finden (milestone)
11. Jobangebote (partner_multiselection, tag=Praxis)
12. Du hast dich nun beworben! (milestone)

## Seeded Data
- 28+ Users, 19 Partners, 12 Steps
- All logos: Emergent static images

## Completed
- [x] All core features, dashboards, i18n, dark mode
- [x] Refactoring: server.py split into modules (2151 -> 952+442 lines) (2026-04-18)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
