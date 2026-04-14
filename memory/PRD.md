# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (cookies + header fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Seeded Data
- 8 Steps: Persönliche Daten (form), Service Antragstellung (partner_selection:Antragstellung), Meilenstein Antragstellung (milestone), FaMed (display), Service Kenntnisprüfung (partner_selection:Kenntnisprüfung), Meilenstein Kenntnisprüfung (milestone), Service Weiterbildung (partner_selection:Weiterbildung, skippable), Meilenstein Job finden (display)
- 3 Partners: ILS (Antragstellung), ILS2 (Kenntnisprüfung), ILS3 (Weiterbildung) - with tags
- German CMS: GERdoctor hero, Über uns, Partner section
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
- i18n (EN/DE), dark mode, notification preferences, CSV export, bulk user actions
