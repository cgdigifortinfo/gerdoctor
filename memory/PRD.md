# GuidedJourney PRD

## Architecture
Frontend: React + Tailwind + Shadcn + Phosphor Icons | Backend: FastAPI + MongoDB | Auth: JWT httpOnly cookies | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## All Features (6 iterations)
- JWT auth (3 roles: user/admin/partner), brute force protection, password reset
- CMS landing page (Home, About, Partners) with admin editor
- User progress stepper (4 configurable steps, form fields, file uploads)
- Admin dashboard: analytics, user mgmt (search/filter/bulk role), step CRUD, partner CRUD
- Partner dashboard: view submissions, edit profile
- Partner-user linking workflow
- Notification preferences (opt-in/out per step)
- CSV export, audit log with action/date filtering
- i18n (EN/DE), dark mode, admin role protection
- Mailgun SMTP email integration

## Test Results: Backend 52/52 (100%), Frontend 95%
