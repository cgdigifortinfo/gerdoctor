# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + header fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Seeded Data
- 8 Steps: Persönliche Daten (form), Service Antragstellung (partner_selection:Antragstellung), Meilenstein Antragstellung (milestone), FaMed (display), Service Kenntnisprüfung (partner_selection:Kenntnisprüfung), Meilenstein Kenntnisprüfung (milestone), Service Weiterbildung (partner_selection:Weiterbildung, skippable), Meilenstein Job finden (display)
- 3 Partners: ILS (Antragstellung), ILS2 (Kenntnisprüfung), ILS3 (Weiterbildung)
- Site Settings: logo_bold_part=GER, logo_light_part=doctor, primary_color=#114f55
- Users: admin@example.com/Admin123!, demo@example.com/Demo123!, partner@example.com/Partner123!

## Features
- JWT auth (3 roles), token in cookie + body response fallback
- Partner tags + tag-filtered partner_selection steps
- Skippable steps, milestone status display, multiupload with document type classification
- Admin: CMS, analytics, user mgmt, step CRUD with reorder, partner CRUD with tags, audit log, settings
- Partner Dashboard: submission list, user detail with full step data view, ability to complete steps for users
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions
- GERdoctor wordmark logo (GER bold, doctor light)

## User Dashboard UI
- Desktop: Single horizontal row of step cards, unified progress bar inside each tile with sequential animation, horizontal scroll with auto-scroll to active step
- Mobile: Vertical accordion with left progress line, auto-scroll to active step

## Completed (Feb 2026)
- [x] Base setup: FastAPI + React + MongoDB + JWT auth
- [x] Mailgun SMTP, Admin Dashboard (CMS, users, partners, steps, audit log, settings)
- [x] i18n (EN/DE), Dark Mode, Complex Step Engine
- [x] User Dashboard redesign: desktop single-row + mobile accordion
- [x] GERdoctor wordmark logo across all pages
- [x] Admin Settings page (site title, logo, color, contact, footer)
- [x] Desktop auto-scroll to active step
- [x] Partner submission detail: full user step data + step completion ability
- [x] Logout single-click fix (tokenRef instead of state)

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
