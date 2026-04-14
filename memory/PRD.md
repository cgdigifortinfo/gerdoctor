# GuidedJourney - Product Requirements Document

## Original Problem Statement
Build a mobile-first app with CMS-style landing page, progress stepper for users, multi-role system (user, admin, partner), admin CMS for managing steps/users/partners, partner dashboard for viewing submissions and editing profile.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI + Phosphor Icons
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Auth**: JWT with httpOnly cookies, role-based access control
- **Email**: Mailgun SMTP integration (gerdoc@digifort-experts.de)
- **File Storage**: Emergent Object Storage (EMERGENT_LLM_KEY)
- **Design**: Swiss & High-Contrast archetype, Cabinet Grotesk + Satoshi fonts

## User Personas
1. **Regular User**: Completes guided onboarding steps (profile, partner selection, application, review)
2. **Admin**: Manages steps, users, partners via CMS dashboard
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
- [x] Configurable email triggers per step (on enter, edit, leave)

## What's Been Implemented (April 2026)
- Complete backend API (auth, steps, partners, files, admin, CMS)
- Landing page with hero, features, about us, partners sections
- Login/Register with split-screen design
- User dashboard with progress stepper
- Admin dashboard with Users/Steps/Partners tabs
- Partner dashboard with submissions/profile tabs
- Mailgun SMTP email integration
- Emergent Object Storage for file uploads
- Default seeded data (4 steps, 3 partners, admin account)

## Prioritized Backlog
### P0 (Critical)
- All core features implemented ✅

### P1 (Important)
- CMS content editor for landing page sections (admin)
- Admin: ability to edit user progress status directly
- Password strength indicator on registration

### P2 (Nice to Have)
- Partner linking workflow (admin links user account to partner org)
- User notification preferences (opt-in/out per step)
- Dashboard analytics for admin (user completion rates)
- Dark mode support
- Multi-language support

## Next Tasks
1. Enhance admin user detail view with progress editing
2. Add CMS editor for landing page content
3. Add partner user linking workflow
4. Add search/filter to admin user list
5. Implement user notification preferences
