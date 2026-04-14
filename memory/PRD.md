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

## User Personas
1. **Regular User**: Completes guided onboarding steps
2. **Admin**: Manages steps, users, partners, CMS content via dashboard
3. **Partner Company**: Views user submissions, edits own profile

## Core Requirements
- [x] Mobile-first responsive design
- [x] CMS-style landing page (Home, About Us, Partners)
- [x] JWT authentication with 3 roles
- [x] Progress stepper (4 configurable steps)
- [x] Admin CMS: manage steps, users, partners
- [x] Partner dashboard: view submissions, edit profile
- [x] File uploads (documents, images)
- [x] Mailgun SMTP email notifications
- [x] Configurable email triggers per step

## What's Been Implemented

### Phase 1 (April 14, 2026)
- Complete backend API (auth, steps, partners, files, admin, CMS)
- Landing page, Login/Register, User Dashboard, Admin Dashboard, Partner Dashboard
- Mailgun SMTP email integration
- Object Storage for file uploads
- Default seeded data (4 steps, 3 partners, admin account)

### Phase 2 (April 14, 2026)
- CMS content editor (admin can edit landing page hero, about, partners text)
- Admin analytics dashboard (stats, user distribution, step completion rates)
- User search/filter (by name, email, role)
- Partner-user linking workflow (link/unlink user accounts to partner orgs)
- Admin can edit user progress status directly

## Prioritized Backlog
### P1 (Important)
- Password strength indicator on registration
- User notification preferences (opt-in/out per step)
- Bulk user actions in admin

### P2 (Nice to Have)
- Dark mode support
- Multi-language support
- Export user data to CSV
- Admin audit log

## Next Tasks
1. Add notification preferences for users
2. Implement bulk actions in admin user list
3. Add CSV export for admin reports
4. Add dark mode toggle
