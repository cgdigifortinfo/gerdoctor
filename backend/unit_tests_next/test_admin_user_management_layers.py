import asyncio
import pytest
from slices.admin_user_management.models import CreateUserCommand
from slices.admin_user_management.service import (
    AdminUserManagementService, DuplicateEmail, InvalidSurvey, UnknownPartner, UserNotFound,
)
from slices.admin_user_management.web import admin_user_http_error
from slices.admin_user_management.repository import MongoAdminUserRepository
from slices.admin_user_management.progress import (
    AdminProgressStepNotFound,
    AdminUserProgressService,
    MongoAdminProgressRepository,
)
from slices.admin_user_management.listing_repository import MongoAdminUserListingRepository
from slices.admin_user_management.listing_service import AdminUserListingService

def run(c): return asyncio.run(c)

class Repo:
    def __init__(self):
        self.users={}; self.partners={}; self.surveys={}; self.steps=[]; self.inserted=None; self.progress=None; self.linked=None; self.updated=[]; self.unlinked=None
    async def search(self,q): self.query=q; return list(self.users.values())
    async def user(self,i): return self.users.get(i)
    async def user_by_email(self,e): return next((u for u in self.users.values() if u.get("email")==e),None)
    async def partner(self,i): return self.partners.get(i)
    async def survey(self,i): return self.surveys.get(i)
    async def insert_user(self,d): self.inserted=dict(d); self.users["new"]={"_id":"new",**d}; return "new"
    async def survey_steps(self,i): return self.steps
    async def insert_progress(self,d): self.progress=list(d)
    async def link_partner(self,p,u): self.linked=(p,u)
    async def update_user(self,i,f): self.updated.append((i,dict(f))); return i != "unchanged"
    async def unlink_partners(self,u,p): self.unlinked=(u,p)

def make(repo=None):
    r=repo or Repo(); audits=[]; protected=[]
    async def groups(ids,role): return list(ids)
    async def default_group(role): return "g-"+role
    async def default_survey(): return {"_id":"default","slug":"default"}
    async def audit(*args): audits.append(args)
    async def protect(*args): protected.append(args)
    return AdminUserManagementService(r,lambda:"now",lambda p:"hash",groups,default_group,default_survey,audit,protect,"admin@example.com","aerzte"),r,audits,protected

def test_search_and_create_default_survey_user():
    s,r,a,_=make(); r.users["u"]={"_id":"u","email":"u@x.de","name":"U","role":"user"}; r.steps=[{"_id":"step","order":1}]
    assert run(s.user("u"))["email"] == "u@x.de" and run(s.user("missing")) is None
    assert run(s.search("U","user"))[0]["id"]=="u"
    created=run(s.create(CreateUserCommand("NEW@X.DE","pw","New","user"),{"_id":"a","email":"a@x.de"}))
    assert created.to_document()["survey_id"]=="default" and r.progress[0]["step_id"]=="step" and a

def test_create_partner_with_groups_and_explicit_survey_paths():
    s,r,_,_=make(); r.partners["p"]={"_id":"p"}
    created=run(s.create(CreateUserCommand("p@x.de","pw","P","partner","p",None,("custom",)),{}))
    assert created.survey_id is None and r.linked==("p","new") and r.inserted["group_ids"]==["custom"]
    s,r,_,_=make(); r.surveys["s"]={"_id":"s","slug":"survey"}
    assert run(s.create(CreateUserCommand("u@x.de","p","U","user",survey_id="s"),{})).survey_slug=="survey"

def test_create_rejects_duplicates_unknown_partner_and_survey():
    s,r,_,_=make(); r.users["u"]={"email":"x@y.de"}
    with pytest.raises(DuplicateEmail): run(s.create(CreateUserCommand("x@y.de","p","X","user"),{}))
    with pytest.raises(UnknownPartner): run(s.create(CreateUserCommand("p@y.de","p","P","partner","missing"),{}))
    with pytest.raises(InvalidSurvey): run(s.create(CreateUserCommand("z@y.de","p","Z","user",survey_id="missing"),{}))

def test_role_bulk_archive_and_permissions_workflows():
    s,r,a,p=make(); r.users={"u":{"email":"u@x.de","role":"user"},"admin":{"email":"admin@example.com"},"unchanged":{"email":"x@x.de"}}
    run(s.change_role("u","partner",{"_id":"a","email":"a"})); assert r.updated[-1][1]["role"]=="partner" and a
    with pytest.raises(UserNotFound): run(s.change_role("missing","user",{}))
    assert run(s.bulk_role(["u","missing","admin","unchanged"],"user"))==1
    run(s.archive("u",{"_id":"a","email":"a"})); assert p==[("u","now")] and r.unlinked==("u",None) and r.updated[-1][1]["is_deleted"] is True
    with pytest.raises(UserNotFound): run(s.archive("missing",{}))
    groups,overrides=run(s.update_permissions("u",["g"],["a"],["b"],lambda x:list(x)))
    assert groups==["g"] and overrides=={"allow":["a"],"deny":["b"]}
    with pytest.raises(UserNotFound): run(s.update_permissions("missing",[],[],[],list))

def test_http_error_mapping_covers_known_and_fallback_errors():
    from slices.admin_user_management.domain import InvalidRole, InvalidPartnerAssignment, PrimaryAdminProtected, ConflictingPermissionOverrides
    errors=[UserNotFound(),InvalidRole(),InvalidPartnerAssignment(),UnknownPartner(),InvalidSurvey(),DuplicateEmail(),PrimaryAdminProtected(),ConflictingPermissionOverrides(),ValueError()]
    assert [admin_user_http_error(e).status_code for e in errors]==[404,400,400,400,400,400,400,400,400]

class Result:
    inserted_id="inserted"
    def __init__(self,modified_count=1): self.modified_count=modified_count
class Cursor:
    def __init__(self,rows): self.rows=rows
    def sort(self,*args): return self
    async def to_list(self,n): return self.rows[:n]
class Collection:
    def __init__(self,rows=()): self.rows=list(rows); self.calls=[]
    def find(self,*args): self.calls.append(("find",args)); return Cursor(list(self.rows))
    async def find_one(self,query,*args): return self.rows[0] if self.rows else None
    async def insert_one(self,d): self.calls.append(("insert",dict(d))); return Result()
    async def insert_many(self,d): self.calls.append(("many",list(d)))
    async def update_one(self,*args): self.calls.append(("one",args)); return Result()
    async def update_many(self,*args): self.calls.append(("many_update",args)); return Result()
class DB:
    def __init__(self):
        oid="0123456789abcdef01234567"
        self.users=Collection(({"_id":oid,"email":"u@x.de"},)); self.partners=Collection(({"_id":oid},)); self.surveys=Collection(({"_id":oid,"is_active":True},)); self.steps=Collection(({"_id":oid,"order":1},)); self.user_progress=Collection()

def test_mongo_repository_all_storage_paths_and_invalid_ids():
    db=DB(); repo=MongoAdminUserRepository(db); oid="0123456789abcdef01234567"
    assert len(run(repo.search({})))==1 and run(repo.user(oid)) and run(repo.user("bad")) is None
    assert run(repo.user_by_email("u@x.de")) and run(repo.partner(oid)) and run(repo.partner("bad")) is None
    assert run(repo.survey(oid)) and run(repo.survey("bad")) is None
    assert run(repo.insert_user({"email":"x"}))=="inserted" and len(run(repo.survey_steps(oid)))==1
    run(repo.insert_progress([])); run(repo.insert_progress([{"x":1}]))
    run(repo.link_partner("bad","u")); run(repo.link_partner(oid,"u"))
    assert run(repo.update_user("bad",{})) is False and run(repo.update_user(oid,{"x":1})) is True
    run(repo.unlink_partners("u",None)); run(repo.unlink_partners("u",oid))


def test_admin_progress_service_writes_revision_and_applies_follow_up_rules():
    calls = []

    class ProgressRepository:
        async def step(self, step_id):
            return {"_id": step_id, "order": 1}

    async def write(**values):
        calls.append(("write", values))

    async def skip(user_id, status):
        calls.append(("skip", user_id, status))

    async def complete(user_id):
        calls.append(("complete", user_id))

    service = AdminUserProgressService(ProgressRepository(), write, skip, complete)
    run(service.update(
        "user", "step", "completed", {"anerkennungsstatus": "granted"},
        {"_id": "admin", "email": "admin@example.com"},
    ))
    written = calls[0][1]
    assert written["data"] == {"anerkennungsstatus": "granted"}
    assert written["actor"] == {
        "id": "admin", "email": "admin@example.com", "role": "admin",
    }
    assert written["change_type"] == "admin_update"
    assert calls[1:] == [("skip", "user", "granted"), ("complete", "user")]


def test_admin_progress_service_handles_missing_and_non_initial_steps():
    calls = []

    class ProgressRepository:
        def __init__(self):
            self.result = None

        async def step(self, step_id):
            return self.result

    repository = ProgressRepository()

    async def record(*args, **kwargs):
        calls.append((args, kwargs))

    service = AdminUserProgressService(repository, record, record, record)
    with pytest.raises(AdminProgressStepNotFound):
        run(service.update("user", "missing", "open", None, {}))
    repository.result = {"_id": "step", "order": 2}
    run(service.update("user", "step", "open", None, {"_id": 7, "email": "a@x.de"}))
    assert len(calls) == 2
    assert calls[0][1]["data"] == {}


def test_mongo_admin_progress_repository_validates_ids_and_rows():
    oid = "0123456789abcdef01234567"
    database = type("Database", (), {"steps": Collection(({"_id": oid},))})()
    repository = MongoAdminProgressRepository(database)
    assert run(repository.step("invalid")) is None
    assert run(repository.step(oid)) == {"_id": oid}
    database.steps.rows = []
    assert run(repository.step(oid)) is None


class ListingRepository:
    def __init__(self):
        self.user_rows = [
            {"_id": "partner-user", "email": "p@x.de", "name": "P", "role": "partner",
             "partner_id": "p1", "group_ids": ["g1"]},
            {"_id": "orphan-user", "email": "o@x.de", "name": "O", "role": "partner",
             "partner_id": "missing"},
            {"_id": "user", "email": "u@x.de", "name": "U", "role": "user"},
            {"_id": "admin", "email": "admin@example.com", "name": "A", "role": "admin"},
        ]
        self.group_rows = [{"_id": "g1", "name": "Partner", "role": "partner"}]
        self.partner_rows = [
            {"_id": "p1", "name": "Alpha", "linked_user_ids": ["partner-user"],
             "registration_status": "active", "is_active": True},
            {"_id": "p2", "name": "Beta", "linked_user_ids": []},
        ]

    async def users(self, limit=1000):
        return self.user_rows[:limit]

    async def groups(self):
        return self.group_rows

    async def partners(self):
        return self.partner_rows

    async def partner_step_ids(self):
        return {"step"}

    async def partner_progress(self, step_ids):
        return [
            {"user_id": "user", "data": {
                "selected_partner_id": "p1", "selected_partner_ids": ["p2", "missing"],
            }},
            {"user_id": "user", "data": {"selected_partner_name": "ALPHA"}},
            {"user_id": "user", "data": {"selected_partner_name": "Ghost"}},
        ]

    async def submissions(self):
        return [{"partner_id": "p1", "user_id": "user"}]

    async def detail(self, user_id):
        if user_id == "missing":
            return None
        return (
            self.user_rows[2],
            [{"step_id": "step", "revision": 1, "status": "completed"}],
            [{"id": "submission"}],
            [{"id": "history"}],
        )

    async def active_steps(self):
        return [{"_id": "step", "title": "Step"}]

    async def progress(self, user_id):
        return [{"step_id": "step", "status": "completed"}] if user_id == "user" else []


def make_listing(repository=None):
    repo = repository or ListingRepository()

    async def statuses(user_ids, partner_id, partner_name):
        return {user_id: {"completed": user_id == "partner-user"} for user_id in user_ids}

    async def metrics(user_ids):
        return {"user": {"completion_pct": 75, "estimated_completion": "soon"}}

    async def revisions(user_id):
        return [{
            "step_id": "step", "revision": 1, "current_step_version": 2,
            "configuration_changed": True, "step_deleted": False,
            "step_snapshot": {"title": "Old"}, "removed_field_names": ["old"],
        }]

    async def completion(user_id):
        return 75

    async def groups(user):
        return [{"id": "g1"}]

    async def permissions(user):
        return ["users.view"]

    return AdminUserListingService(
        repo, statuses, metrics, revisions, completion, groups, permissions,
        "admin@example.com",
    )


def test_admin_user_listing_resolves_partners_orphans_groups_and_counts():
    rows = run(make_listing().users())
    partner, orphan, user, admin = rows
    assert partner["partner_names"] == ["Alpha"]
    assert partner["pending_registrations"] == 1
    assert partner["permission_groups"] == [{"id": "g1", "name": "Partner", "role": "partner"}]
    assert orphan["orphaned_partner_references"] == [{"type": "partner_id", "value": "missing"}]
    assert set(user["partner_names"]) == {"Alpha", "Beta"}
    assert {item["value"] for item in user["orphaned_partner_references"]} == {"missing", "Ghost"}
    assert user["pending_registrations"] == 1
    assert user["completion_pct"] == 75
    assert admin["pending_registrations"] is None and admin["completion_pct"] == 0


def test_admin_user_listing_detail_and_csv_export():
    service = make_listing()
    assert run(service.detail("missing")) is None
    detail = run(service.detail("user"))
    assert detail["progress"][0]["configuration_changed"] is True
    assert detail["effective_permissions"] == ["users.view"]
    assert detail["is_primary_admin"] is False and detail["completion_pct"] == 75
    exported = run(service.csv_export())
    assert exported.splitlines()[0] == "Name,Email,Role,Created At,Step"
    assert "U,u@x.de,user,,completed" in exported


def test_mongo_admin_user_listing_repository_all_read_paths():
    oid = "0123456789abcdef01234567"
    database = type("ListingDatabase", (), {
        "users": Collection(({"_id": oid},)),
        "permission_groups": Collection(({"_id": oid},)),
        "partners": Collection(({"_id": oid},)),
        "steps": Collection(({"_id": oid},)),
        "user_progress": Collection(({"user_id": oid},)),
        "partner_submissions": Collection(({"user_id": oid},)),
        "progress_history": Collection(({"user_id": oid},)),
    })()
    repository = MongoAdminUserListingRepository(database)
    assert run(repository.users()) and run(repository.groups()) and run(repository.partners())
    assert run(repository.partner_step_ids()) == {oid}
    assert run(repository.partner_progress(set())) == []
    assert run(repository.partner_progress({oid})) and run(repository.submissions())
    assert run(repository.detail("invalid")) is None
    assert run(repository.detail(oid)) is not None
    assert run(repository.active_steps()) and run(repository.progress(oid))
    database.users.rows = []
    assert run(repository.detail(oid)) is None
