# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + header fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Partner tags, Skippable steps, Multiupload with doc types
- Admin: CMS, analytics, user mgmt, step CRUD with reorder, partner CRUD, audit log, settings
- Partner Dashboard: submission list with forecast, user detail with step data + step completion
- Step Duration & Estimated Completion: each step has duration_value + duration_unit, system predicts journey completion date
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions
- GERdoctor wordmark logo (GER bold, doctor light)

## Step Duration
- Each step: `duration_value` (int, 0=instant) + `duration_unit` (days/weeks/months/years)
- Seeded: Step 1=0d, Step 2=0d, Step 3=4w, Step 4=0d, Step 5=0d, Step 6=3m, Step 7=0d, Step 8=2w
- Calculation: start from completed_at of last completed step → add remaining step durations
- Progress records: started_at (on enter), completed_at (on complete)
- Displayed: User (header banner), Admin (user list Forecast column), Partner (submissions Forecast column)
- Admin editable via step editor (Grunddaten → Dauer)

## Completed
- [x] Base setup, Auth, Mailgun SMTP, Admin Dashboard
- [x] i18n, Dark Mode, Complex Step Engine, Email Templates
- [x] User Dashboard: desktop single-row cards + mobile accordion
- [x] GERdoctor wordmark logo, Admin Settings page
- [x] Desktop auto-scroll, Partner detail with step data + completion
- [x] Logout single-click fix, Duplicate submission fix
- [x] Step Duration & Estimated Completion (all roles)

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
