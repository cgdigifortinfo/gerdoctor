# GuidedJourney - Product Requirements Document

## Architecture
- Frontend: React + Tailwind CSS + Shadcn UI + Phosphor Icons
- Backend: FastAPI + MongoDB (Motor)
- Auth: JWT httpOnly cookies, RBAC (user/admin/partner)
- Email: Mailgun SMTP
- Storage: Emergent Object Storage
- Colors: Primary #114f55, Secondary #9ec5aa
- i18n: EN/DE via React Context
- Theme: Light/Dark via CSS variables

## Implemented Features (All Phases)

### Phase 1: Core MVP
- JWT auth, landing page, user stepper, admin/partner dashboards
- Mailgun email, Object Storage uploads, 4 default steps, 3 partners

### Phase 2: CMS & Analytics
- CMS content editor, analytics dashboard, user search/filter, partner-user linking

### Phase 3: Preferences & Bulk
- Notification preferences (opt-in/out per step), bulk role change, CSV export
- Color scheme migration to #114f55/#9ec5aa, admin role protection

### Phase 4: i18n, Audit, Dark Mode (Current)
- Multi-language support (English/German) with language toggle
- Admin audit log tracking all admin actions (role changes, CRUD, CMS updates)
- Dark mode toggle with localStorage persistence
- All pages use semantic Tailwind classes for theme compatibility

## Test Results
- Backend: 36/36 endpoints (100%)
- Frontend: 95% (1 minor mobile toggle visibility)
