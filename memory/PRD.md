# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Admin User Create dialog
- Admin: CMS, analytics, user mgmt, step CRUD, partner CRUD (multi-user linking), audit log, settings
- Partner Dashboard: 2 tabs (Meine/Andere Nutzer), sortable/filterable, user detail + step completion
- Step types: form, partner_selection, partner_multiselection, milestone, display
- Step Duration & Estimated Completion, Fachgebiet filter, Forecast date filter
- All overlays max-h + overflow-y-auto for screen-safe dialogs

## Step Types
- form: dynamic form fields
- partner_selection: tag-filtered partner list (single selection)
- partner_multiselection: tag-filtered partner list (MULTIPLE selections, submits to all)
- milestone: pending/complete status display
- display: info + action buttons

## Test Coverage (70+ tests)
- test_impersonation.py, test_partner_api.py, test_partner_dashboard_v2.py
- test_settings_api.py, test_step_duration.py, test_iteration17_features.py
- test_iteration24_features.py (create user, partner multi-link, multiselection)

## Completed
- [x] Base setup, Auth, Mailgun SMTP, Admin Dashboard
- [x] i18n, Dark Mode, Complex Step Engine, Email Templates
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] GERdoctor wordmark logo, Admin Settings, Admin Impersonate
- [x] Partner detail with step data + file downloads + completion
- [x] Step Duration & Estimated Completion (all roles)
- [x] Partner Dashboard: 2 tabs, sortable columns, Fachgebiet + Forecast filter
- [x] Overlay max-h + overflow-y-auto fix across all dialogs
- [x] Partner editor: multi-user linking with checkboxes (role "partner")
- [x] Admin User Create dialog (Name, Email, Password, Role, optional Partner)
- [x] partner_multiselection step type (multi-partner selection + submit-multi API)

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
