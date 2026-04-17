# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Admin User CRUD
- Admin: CMS, analytics, user mgmt, step CRUD (5 types), partner CRUD (m:n linking), audit log, settings
- Partner Dashboard: 2 tabs (Meine/Andere Nutzer), sortable/filterable, user detail + step completion
- Partner Step Completion: emails, next step activation, progress history
- Partner can view ALL user step data; partner selection choices hidden for other partners
- Step types: form, partner_selection, partner_multiselection, milestone, display
- Step Duration & Estimated Completion, Fachgebiet filter (15 specialties)
- Progress % excludes steps with duration_value=0
- User step-back navigation restores form data and partner selections

## Data Model
- **1:1 Dashboard Access**: `partner.user_id` + `user.partner_id` + `user.role='partner'`
- **M:N Linking** (no role change): `partner.linked_user_ids[]`
- **Step Submissions**: `partner_submissions` collection
- **Completion %**: Only steps with `duration_value > 0` count
- `partner_step_id`: partner_selection step matching partner's tag

## Seeded Data
- 28 Users (1 Admin, 17 Partner, 10 User), 17 Partners, 10 Steps
- Steps with duration: Step 3 (4 weeks), Step 6 (3 months)

## Completed
- [x] All core features, dashboards, i18n, dark mode
- [x] Seed migration with realistic partners + demo users
- [x] Partner-User m:n relationship (no role change)
- [x] Partner Step Completion with emails + next step
- [x] Partner views ALL user data (selections hidden) (2026-04-17)
- [x] Progress % excludes duration=0 steps (2026-04-17)
- [x] User step-back restores form data + partner selections (2026-04-17)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
