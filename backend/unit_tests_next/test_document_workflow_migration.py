import asyncio

from slices.document_workflow.migration import migrate_document_workflows


class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, *_args): return self
    async def to_list(self, _limit): return list(self.rows)


class Steps:
    def __init__(self, rows): self.rows, self.updates = rows, []
    async def distinct(self, _field): return ["survey"] if self.rows else []
    def find(self, _query): return Cursor(self.rows)
    async def update_one(self, query, update, **_kwargs): self.updates.append((query, update))


class Settings:
    def __init__(self, version): self.version, self.updates = version, []
    async def find_one(self, *_args): return {"document_workflow_version": self.version}
    async def update_one(self, query, update, **kwargs): self.updates.append((query, update, kwargs))


class Database:
    def __init__(self, version, rows): self.site_settings, self.steps = Settings(version), Steps(rows)


def run(database):
    return asyncio.run(migrate_document_workflows(database, lambda survey_id: {"survey_id": survey_id}))


def test_migration_is_noop_after_current_version():
    database = Database(2, [])
    assert run(database) == 0
    assert database.site_settings.updates == []


def test_migration_marks_empty_database_current():
    database = Database(0, [])
    assert run(database) == 0
    assert database.site_settings.updates[0][1] == {"$set": {"document_workflow_version": 2}}


def workflow_rows(existing_locks=False, titles=True):
    upload_lock = {"action": "read_only", "source_step_order": 2, "field": "files", "operator": "has_upload"}
    milestone_lock = {"action": "read_only", "source_step_order": 4, "field": "partner_uploads", "operator": "has_upload"}
    conditions = [upload_lock, milestone_lock] if existing_locks else []
    return [
        {"_id": "orphan", "order": 0, "step_type": "form"},
        {"_id": "decision", "order": 1, "step_type": "decision", "conditions": list(conditions)},
        {"_id": "other", "order": 1.5, "step_type": "form", "fields": []},
        {"_id": "upload", "order": 2, "step_type": "form",
         "title": "Dokumente Prüfung" if titles else "Upload",
         "fields": [{"name": "ignored", "field_type": "text"}, {"name": "files", "field_type": "multiupload"}],
         "conditions": list(conditions)},
        {"_id": "partner", "order": 3, "step_type": "partner_selection", "conditions": list(conditions)},
        {"_id": "milestone", "order": 4, "step_type": "milestone",
         "title": "Übersicht Prüfung" if titles else "Result"},
    ]


def test_migration_swaps_legacy_titles_and_adds_all_locks():
    database = Database(0, workflow_rows())
    assert run(database) == 8
    assert len(database.steps.updates) == 5
    assert database.steps.updates[0][1]["$set"]["title"] == "Übersicht Prüfung"
    assert len(database.steps.updates[-1][1]["$set"]["conditions"]) == 2


def test_migration_preserves_titles_and_existing_locks():
    database = Database(1, workflow_rows(existing_locks=True, titles=False))
    assert run(database) == 0
    assert database.steps.updates == []


def test_migration_ignores_incomplete_blocks():
    rows = [
        {"_id": "decision", "order": 1, "step_type": "decision"},
        {"_id": "plain", "order": 2, "step_type": "form", "fields": []},
        {"_id": "milestone", "order": 3, "step_type": "milestone"},
        {"_id": "decision2", "order": 4, "step_type": "decision"},
        {"_id": "upload", "order": 5, "step_type": "form", "fields": [{"name": "f", "field_type": "file"}]},
        {"_id": "milestone2", "order": 6, "step_type": "milestone"},
    ]
    assert run(Database(1, rows)) == 0
