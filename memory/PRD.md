# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Partner Dashboard with 2 user tabs
- Admin: CMS, analytics, user mgmt, step CRUD, partner CRUD, audit log, settings
- Partner: "Meine Nutzer" (submitted) + "Andere Nutzer" (not submitted), sortable/filterable tables, user detail with step data + step completion
- Step Duration & Estimated Completion, Fachgebiet filter, Forecast date filter
- User Dashboard: sticky header with teal "Abschluss" badge, desktop/mobile responsive
- i18n (EN/DE), dark mode, notification preferences, CSV export, GERdoctor wordmark logo

## Test Coverage (58+ tests)
- test_impersonation.py: 7 tests
- test_partner_api.py: 10 tests  
- test_partner_dashboard_v2.py: 14 tests (new: tabs, sorting, filtering, other-users)
- test_settings_api.py: 14 tests
- test_step_duration.py: 7 tests
- test_iteration17_features.py: 6 tests

## Completed
- [x] Base setup, Auth, Mailgun SMTP, Admin Dashboard (CMS, analytics, users, steps, partners, audit, settings)
- [x] i18n, Dark Mode, Complex Step Engine, Email Templates
- [x] User Dashboard: desktop single-row cards + mobile accordion, sticky header forecast badge
- [x] GERdoctor wordmark logo, Admin Settings, Admin Impersonate
- [x] Partner detail with step data + file downloads + step completion
- [x] Step Duration & Estimated Completion (all roles)
- [x] Partner Dashboard: 2 tabs (Meine/Andere Nutzer), sortable columns, Fachgebiet + Forecast filter

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
