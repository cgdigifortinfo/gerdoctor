# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + header fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Seeded Data
- 8 Steps: Persönliche Daten (form), Service Antragstellung (partner_selection:Antragstellung), Meilenstein Antragstellung (milestone), FaMed (display), Service Kenntnisprüfung (partner_selection:Kenntnisprüfung), Meilenstein Kenntnisprüfung (milestone), Service Weiterbildung (partner_selection:Weiterbildung, skippable), Meilenstein Job finden (display)
- 3 Partners: ILS (Antragstellung), ILS2 (Kenntnisprüfung), ILS3 (Weiterbildung) - with tags
- German CMS: GERdoctor hero, Über uns, Partner section
- Site Settings: logo_bold_part=GER, logo_light_part=doctor, primary_color=#114f55
- Users: admin@example.com/Admin123!, demo@example.com/Demo123!, partner@example.com/Partner123!

## Field Types
- text, email, phone, textarea, date, file, select, selectbox, multiupload (extendable list with document type: Visum, Antrag auf Approbation, Approbation, Eingangsbescheinigung, Kenntnissprüfung)

## Step Types
- form: dynamic form fields | partner_selection: tag-filtered partner list | milestone: pending/complete status display | display: info + action buttons

## Features
- JWT auth (3 roles), token in cookie + body response fallback
- Partner tags + tag-filtered partner_selection steps
- Skippable steps, milestone status display
- Multiupload with document type classification
- Admin: CMS, analytics, user mgmt, step CRUD with reorder, partner CRUD with tags, audit log with filtering
- Admin Settings: site title, logo wordmark (bold/light parts), contact email, primary color, footer text, meta description
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions
- GERdoctor wordmark logo (GER bold, doctor light) across all pages

## User Dashboard UI
- Desktop: Horizontal grid of step cards (max 4 cols) with progress bars at top, animated fill on load, active step highlighted
- Mobile: Vertical accordion with left progress line, auto-scroll to active step, expand/collapse on tap
- Smooth CSS transitions and staggered entry animations

## Completed (Feb 2026)
- [x] Base setup: FastAPI + React + MongoDB + JWT auth
- [x] Mailgun SMTP Email Integration
- [x] Admin Dashboard: CMS, users, partners, steps, audit log
- [x] Tailwind color overhaul (Primary: #114f55, Secondary: #9ec5aa)
- [x] i18n (EN/DE) and Dark Mode
- [x] Complex Step Engine: multiupload, selectbox, conditions, field mapping
- [x] Email Template editor per step
- [x] User History Timeline
- [x] User Dashboard redesign: desktop horizontal cards + mobile accordion with progress animations
- [x] GERdoctor wordmark logo component integrated across all pages
- [x] Admin Settings page: site title, logo config, contact email, primary color, footer text

## Backlog
- [ ] P1: Step template library (save/reuse step configurations)
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration for external system notifications
