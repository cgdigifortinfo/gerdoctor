# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + Bearer fallback, Bearer prioritized) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Partner tags, Skippable steps, Multiupload with doc types
- Admin: CMS, analytics, user mgmt, step CRUD, partner CRUD, audit log, settings
- Admin Impersonation: Login as any user, red "Beenden" button to exit, Bearer token injection via axios interceptor
- Partner Dashboard: submission list with forecast, user detail with step data + file downloads + step completion
- Step Duration & Estimated Completion: per-step duration (days/weeks/months/years), predicted journey end date
- User Dashboard: sticky header with teal "Abschluss" badge, desktop/mobile responsive
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions

## Test Coverage (44 tests)
- test_impersonation.py: 7 tests (impersonate flow, auth, audit)
- test_partner_api.py: 10 tests (user detail, access control, progress update, logout)
- test_settings_api.py: 14 tests (settings CRUD, existing APIs, admin dashboard)
- test_step_duration.py: 7 tests (duration fields, estimated completion, timestamps)
- test_iteration17_features.py: 6 tests (duplicate fix, step data display)

## Completed
- [x] Base setup, Auth, Mailgun SMTP, Admin Dashboard
- [x] i18n, Dark Mode, Complex Step Engine, Email Templates
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] GERdoctor wordmark logo, Admin Settings page
- [x] Partner detail with step data + file downloads + completion
- [x] Step Duration & Estimated Completion (all roles)
- [x] Estimated completion in sticky header (teal pill badge)
- [x] Admin Impersonate with Bearer token priority fix
- [x] Full test suite: 44 tests passing

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
