# GERdoctor - Praktizieren in Deutschland

## Architecture
Frontend: React + Tailwind + Shadcn | Backend: FastAPI + MongoDB | Auth: JWT (Bearer priority + cookie fallback) | Email: Mailgun SMTP | Storage: Emergent Object Storage | i18n: EN/DE | Theme: Light/Dark

## Features
- JWT auth (3 roles), Admin Impersonation, Admin User CRUD
- Admin: CMS, analytics, user mgmt, step CRUD (5 types), partner CRUD (m:n linking), audit log, settings
- Partner Dashboard: 2 tabs, user detail + step completion, emails, next step activation
- Partner can view ALL user step data; partner selection choices hidden for other partners
- Step types: form, partner_selection, partner_multiselection, milestone, display
- Partner tag/category filter dropdown on selection views
- Step Duration & Estimated Completion (excludes duration=0 steps)
- User step-back navigation restores form data, partner selections, multi-partner selections
- Landing page: medical hero image, "by digiFORT" branding, German headlines
- FaMed step with external link to famed-test.de
- Tooltip "Voraussichtliche Approbation" on user header date

## Steps (12 total)
1. Persoenliche Daten (form)
2. Antragstellung Approbation (partner_selection, tag=Antragstellung)
3. Uebersicht Antragstellung Approbation (milestone, 4 weeks)
4. FaMed (display, link to famed-test.de)
5. Gleichwertigkeitspruefung (partner_selection, tag=Gleichwertigkeitspruefung)
6. Uebersicht Gleichwertigkeitspruefung (milestone, 3 months)
7. Service Kenntnisprüfung (partner_selection, tag=Kenntnisprüfung)
8. Meilenstein Kenntnisprüfung (milestone, 3 months)
9. Service Weiterbildung (partner_selection, tag=Weiterbildung)
10. Meilenstein Job finden (milestone)
11. Jobangebote (partner_multiselection, tag=Praxis)
12. Du hast dich nun beworben! (milestone)

## Partners (19 total)
- Antragstellung (3): ILS, digiFORT Experts, HABS e.V.
- Gleichwertigkeitspruefung (2): IQB Pruefungszentrum, MedAkademie Berlin
- Kenntnisprüfung (2): ILS2, HC&S
- Weiterbildung (3): ILS3, Lingoda, InterPers
- Praxis (9): Hausarztpraxis, Internistische, Chirurgische, Kinderarzt, Hautarzt, Neurologisches, Orthopaedische, Frauenarzt, Praxis am Hang

## Seeded Data
- 28 Users, 19 Partners, 12 Steps
- All logos: Emergent static images

## Completed
- [x] All core features, dashboards, i18n, dark mode
- [x] Partner-User m:n relationship, Partner Step Completion
- [x] Landing page: hero doctors image, headlines, badge, partner filter (2026-04-17)
- [x] "by digiFORT" branding in logo (2026-04-17)
- [x] Step restructuring: Gleichwertigkeitspruefung steps + partners (2026-04-17)
- [x] FaMed link, step renames, tooltip fix (2026-04-17)

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
