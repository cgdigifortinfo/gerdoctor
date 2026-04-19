# GERdoctor - Praktizieren in Deutschland

## Architecture
```
/app/backend/
  server.py, database.py, models.py, auth.py, helpers.py
  server.py.backup (pre-refactor)
  tests/ (4 test suites, 85+ tests)
```

## Cascade Delete Rules
- **Partner delete**: submissions deleted, partner-users reverted to role "user"
- **User delete**: progress, submissions, history, files deleted; removed from partner.linked_user_ids; partner.user_id unset
- **Step delete**: user_progress and progress_history for that step deleted

## Test Coverage
- test_e2e_step_walkthrough.py: 15 tests (full 12-step user journey)
- test_crud_and_validation.py: 29 tests (CRUD + cascade + negative inputs)
- test_partner_linking.py: 13 tests (m:n linking)
- test_partner_step_completion.py: 16 tests

## Partners (22)
- Antragstellung: ILS, digiFORT Experts, HABS e.V., InterPers, FIA Academy, FaMed
- Gleichwertigkeitspruefung: IQB, MedAkademie Berlin
- Kenntnisprüfung: ILS2, HC&S, FIA Academy
- Weiterbildung: ILS3, Lingoda, InterPers
- Praxis: 9 Arztpraxen + PraxisConnect

## Backlog
- [ ] P1: Step template library
- [ ] P1: Bulk import/export for step configurations
- [ ] P2: Webhook integration
