# GERdoctor - Praktizieren in Deutschland

## Architecture
```
/app/backend/
  server.py, database.py, models.py, auth.py, helpers.py
  tests/ (4 suites, 90 tests)
```

## i18n System
- **UI strings**: LanguageContext.js with DE/EN translations (150+ keys)
- **Steps**: `translations` field per step: `{en: {title, description, ...}}`
- **CMS**: `translations` field per section: `{en: {hero_title, hero_subtitle, ...}}`
- **Admin**: DE/EN tabs in Step Editor and CMS Editor
- **Frontend**: `localize(item, field)` and `localizeCms(content, field, trans)` helpers
- Default language: German (stored in main fields), EN in `translations.en`

## Completed
- [x] i18n for Steps and CMS content (2026-04-20)
- [x] Admin Step Editor: EN translation tab
- [x] Admin CMS Editor: DE/EN toggle per section
- [x] All 12 steps translated to English
- [x] All 3 CMS sections translated to English
- [x] Landing page uses localized CMS content

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
