# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + header fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Partner tags, Skippable steps, Multiupload with doc types
- Admin: CMS, analytics, user mgmt, step CRUD, partner CRUD, audit log, settings
- Admin Impersonation: Login as any user, red "Beenden" button to exit
- Partner Dashboard: submission list with forecast, user detail with step data + step completion
- Step Duration & Estimated Completion: per-step duration, predicted journey end date
- User Dashboard: sticky header with teal "Abschluss" badge, desktop/mobile responsive
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions
- GERdoctor wordmark logo (GER bold, doctor light)

## Completed
- [x] Base setup, Auth, Mailgun SMTP, Admin Dashboard
- [x] i18n, Dark Mode, Complex Step Engine, Email Templates
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] GERdoctor wordmark logo, Admin Settings page
- [x] Partner detail with step data + file downloads + completion
- [x] Step Duration & Estimated Completion (all roles)
- [x] Estimated completion in sticky header (teal pill badge)
- [x] Admin Impersonate: UserSwitch button, red Beenden exit, audit logged

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
