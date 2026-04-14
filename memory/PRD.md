# GuidedJourney - Product Requirements Document

## Original Problem Statement
Build a mobile-first app with CMS-style landing page, progress stepper for users, multi-role system (user, admin, partner), admin CMS for managing steps/users/partners, partner dashboard for viewing submissions and editing profile.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Phosphor Icons
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Auth**: JWT with httpOnly cookies, role-based access control
- **Email**: Mailgun SMTP (smtp.eu.mailgun.org)
- **File Storage**: Emergent Object Storage
- **Design**: Swiss & High-Contrast archetype, Cabinet Grotesk + Satoshi fonts
- **Colors**: Primary #114f55, Secondary #9ec5aa

## What's Been Implemented

### Phase 1: Core MVP
- JWT auth with 3 roles, landing page, user dashboard with stepper, admin dashboard, partner dashboard
- Mailgun SMTP email, Object Storage file uploads

### Phase 2: CMS & Analytics
- CMS content editor for landing page, analytics dashboard, user search/filter, partner-user linking

### Phase 3: Preferences & Bulk Actions (Current)
- User notification preferences (opt-in/out per step: enter, edit, leave)
- Bulk user actions (multi-select checkboxes + batch role change)
- CSV export for admin reporting (users + step statuses)
- Complete color scheme migration to #114f55 / #9ec5aa
- Admin role protection (seed admin can't be demoted)

## Prioritized Backlog
### P1: Dark mode, multi-language
### P2: Audit log, password strength indicator, bulk user delete
