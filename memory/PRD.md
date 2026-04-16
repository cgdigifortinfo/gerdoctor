# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Admin User CRUD (create + delete)
- Admin: CMS, analytics, user mgmt, step CRUD (5 types), partner CRUD (multi-user linking), audit log, settings
- Partner Dashboard: 2 tabs (Meine/Andere Nutzer), sortable/filterable, user detail + step completion
- **Partner Step Completion**: Partner can complete steps for users, sends emails, activates next step
- Step types: form, partner_selection, partner_multiselection, milestone, display
- Step editor: type-specific field visibility, global tabs for all types
- Admin user detail: shows completed step data inline
- Step Duration & Estimated Completion, Fachgebiet filter (15 specialties), Forecast date filter

## Data Model: Partner-User Relationship
- **1:1 Dashboard Access**: `partner.user_id` + `user.partner_id` + `user.role='partner'` (for login)
- **M:N Linking** (no role change): `partner.linked_user_ids[]` on partner doc
- **Step Submissions**: `partner_submissions` collection (when user selects partner in step)
- Partner Dashboard "Meine Nutzer" = UNION of submissions + linked_user_ids
- `partner_step_id`: Identifies the partner_selection step matching the partner's tag

## Seeded Data (Updated 2026-04-16)
- 28 Users: 1 Admin, 17 Partner-Users, 10 Regular Users
- 17 Partners with logos (3 Antragstellung, 2 Kenntnispruefung, 3 Weiterbildung, 9 Praxis)
- 8 Steps, 15 medical specialties, German CMS

## Test Coverage
- 80+ existing tests + 13 partner linking tests + 16 step completion tests
- All test files use TEST_ prefix cleanup

## Completed
- [x] All core features (auth, steps, partners, CMS, audit, settings)
- [x] User Dashboard, Partner Dashboard, Admin Impersonation
- [x] Seed migration: realistic partners + demo users
- [x] Partner-User m:n relationship (no role change)
- [x] Partner Step Completion with emails + next step activation (2026-04-16)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
