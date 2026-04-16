# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Admin User CRUD (create + delete)
- Admin: CMS, analytics, user mgmt, step CRUD (5 types), partner CRUD (multi-user linking), audit log, settings
- Partner Dashboard: 2 tabs (Meine/Andere Nutzer), sortable/filterable, user detail + step completion
- Step types: form, partner_selection, partner_multiselection, milestone, display
- Step editor: type-specific field visibility, global tabs for all types
- Admin user detail: shows completed step data inline (like partner view)
- Step Duration & Estimated Completion, Fachgebiet filter (15 specialties), Forecast date filter

## Seeded Data (Updated 2026-04-16)
- 5 preserved accounts: admin, partner@example.com, cg@digifort.info, doc1@chrizz1001.de, praxis_am_hang@chrizz1001.de
- 8 new demo doctors with varying step progress (0-8/8 steps)
- 9 partners total (4 updated originals + 5 new) with logos from digifort-experts.de
- Partner categories: Antragstellung (3), Kenntnisprüfung (2), Weiterbildung (3), HNO (1)
- 15 medical specialties in Fachgebiet selectbox
- 8 steps, German CMS

## Test Coverage (80+ tests, with cleanup)
All test files delete TEST_ prefixed data after execution.

## Completed
- [x] All core features (auth, steps, partners, CMS, audit, settings)
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] Partner Dashboard: 2 tabs, sorting, filtering, step data + completion
- [x] Admin Impersonate, User Create/Delete, Partner multi-user linking
- [x] partner_multiselection step type (multi-partner selection)
- [x] Admin user detail with step data inline
- [x] Step editor: partner_multiselection in dropdown, conditional field visibility
- [x] Seeded demo doctors with Fachgebiete
- [x] Test cleanup (TEST_ prefixed data deleted)
- [x] Seed migration: realistic partners with logos, demo users with varying progress (2026-04-16)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
