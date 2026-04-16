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

## Data Model: Partner-User Relationship
- **1:1 Dashboard Access**: `partner.user_id` + `user.partner_id` + `user.role='partner'` (for login/dashboard)
- **M:N Linking** (no role change): `partner.linked_user_ids[]` array on partner doc. Users keep their role.
- **Step Submissions**: `partner_submissions` collection (when user selects partner in step)
- Partner Dashboard "Meine Nutzer" = UNION of submissions + linked_user_ids

## Seeded Data (Updated 2026-04-16)
- **28 Users**: 1 Admin, 17 Partner-Users, 10 Regular Users
- **5 beibehaltene Accounts**: admin, partner@example.com, cg@digifort.info, doc1@chrizz1001.de, praxis_am_hang@chrizz1001.de
- **8 Demo-Aerzte** mit Fortschritt 0-8/8 Steps
- **17 Partner** mit Logos von digifort-experts.de (3 Antragstellung, 2 Kenntnispruefung, 3 Weiterbildung, 9 Praxis)
- 15 medical specialties, 8 Steps, German CMS

## Test Coverage
- 80+ existing tests + 13 new partner linking tests (test_partner_linking.py)
- All test files delete TEST_ prefixed data after execution

## Completed
- [x] All core features (auth, steps, partners, CMS, audit, settings)
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] Partner Dashboard: 2 tabs, sorting, filtering, step data + completion
- [x] Admin Impersonate, User Create/Delete, Partner multi-user linking
- [x] partner_multiselection step type
- [x] Admin user detail with step data inline
- [x] Seed migration: realistic partners + demo users (2026-04-16)
- [x] Seed migration v2: Praxis partners + service partner users (2026-04-16)
- [x] Partner-User m:n Beziehung (no role change), empty email fix, Tests (2026-04-16)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
