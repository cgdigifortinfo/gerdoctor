from __future__ import annotations
import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from slices.identity_access.domain import (
    initial_progress, login_identifier, login_is_locked, normalized_email,
    partner_registration_documents, user_registration_document,
)
from slices.identity_access.repository import MongoIdentityRepository
from slices.identity_access.service import (
    DuplicateEmail, ExpiredResetToken, IdentityAccessService, InvalidCredentials,
    InvalidResetToken, LoginLocked,
)
from slices.identity_access.web import account_http_error

def run(value): return asyncio.run(value)
NOW=datetime(2026,8,24,tzinfo=timezone.utc)

def test_registration_and_login_domain_documents():
    assert normalized_email("A@B.DE")=="a@b.de" and login_identifier("ip","A@B.DE")=="ip:a@b.de"
    survey={"_id":"s","slug":"pflege"}
    user=user_registration_document("A@B.DE","hash","Name",survey,"g","now","default")
    assert user=={"email":"a@b.de","password_hash":"hash","name":"Name","role":"user","profile":{},
        "survey_id":"s","survey_slug":"pflege","created_at":"now","group_ids":["g"],
        "permission_overrides":{"allow":[],"deny":[]}}
    assert user_registration_document("a","h","n",{"_id":"s"},None,"n","fallback")["group_ids"]==[]
    assert user_registration_document("a","h","n",{"_id":"s"},None,"n","fallback")["survey_slug"]=="fallback"
    account,partner=partner_registration_documents({"email":"P@X.DE","contact_name":"P","company_name":"C",
        "country":"fr","description":"Details","website":"https://example.org"},"h","g","now")
    assert account=={"email":"p@x.de","password_hash":"h","name":"P","role":"partner","profile":{},
        "created_at":"now","group_ids":["g"],"permission_overrides":{"allow":[],"deny":[]},
        "registration_source":"partner_self_service"}
    assert partner=={"name":"C","description":"Details","website":"https://example.org","contact_email":"p@x.de","country":"FR",
        "category":"","tags":[],"linked_user_ids":[],"survey_ids":[],"is_active":False,
        "registration_status":"pending","registration_source":"self_service","registered_at":"now",
        "created_at":"now","billing_status":"pending","access_unlocked":False,
        "billing_settings":{"legal_name":"C","country":"FR","default_currency":"eur"}}
    _, fallback=partner_registration_documents({"email":"p","contact_name":"P","company_name":"C"},"h",None,"now")
    assert fallback["country"]=="DE" and fallback["description"]=="" and account["group_ids"]==["g"]
    steps=[{"_id":1,"order":2}]
    assert initial_progress("u","s",steps,"now")==[{"user_id":"u","step_id":"1","survey_id":"s",
        "step_order":2,"status":"pending","data":{},"created_at":"now","updated_at":"now"}]
    assert login_is_locked(None,NOW) is False and login_is_locked({"count":4},NOW) is False
    assert login_is_locked({"other":1},NOW) is False
    assert login_is_locked({"count":5,"lockout_until":(NOW+timedelta(seconds=1)).isoformat()},NOW) is True
    assert login_is_locked({"count":5},NOW) is False
    assert login_is_locked({"count":5,"lockout_until":NOW.isoformat()},NOW) is False

class Repo:
    def __init__(self):
        self.users={}; self.partners=[]; self.attempt=None; self.progress=[]; self.reset=None; self.failed=None; self.cleared=[]
    async def find_user(self,user_id):
        if user_id=="raise": raise ValueError
        return self.users.get(str(user_id))
    async def user_by_email(self,email): return next((u for u in self.users.values() if u.get("email")==email),None)
    async def insert_user(self,document): self.users["uid"]={"_id":"native",**document}; return "uid","native"
    async def update_user(self,user_id,fields):
        target=self.users.get("uid") or self.users.get(str(user_id)); target.update(fields)
    async def steps(self,survey_id): return [{"_id":"step","order":1}]
    async def insert_progress(self,documents): self.progress.extend(documents)
    async def insert_partner(self,document): self.partners.append(dict(document)); return "pid"
    async def login_attempt(self,identifier): return self.attempt
    async def record_failed_login(self,identifier,until): self.failed=(identifier,until)
    async def clear_login_attempt(self,identifier): self.cleared.append(identifier)
    async def consume_reset_tokens(self,user_id): self.consumed=user_id
    async def insert_reset_token(self,document): self.reset=dict(document)
    async def reset_token(self,token): return self.reset if self.reset and self.reset["token"]==token and not self.reset.get("used") else None
    async def mark_reset_token_used(self,token): self.reset["used"]=True

def test_service_registration_partner_and_duplicate_paths():
    repo=Repo(); service=IdentityAccessService(repo); survey={"_id":"s","slug":"slug"}
    result=run(service.register_user({"email":"A@X.DE","name":"A"},survey,"g","hash","now","fallback"))
    assert result.user_id=="uid" and len(repo.progress)==1
    with pytest.raises(DuplicateEmail): run(service.register_user({"email":"a@x.de","name":"A"},survey,None,"h","n","f"))
    repo=Repo(); service=IdentityAccessService(repo)
    partner=run(service.register_partner({"email":"P@X.DE","contact_name":"P","company_name":"C","country":"DE"},None,"h","now"))
    assert partner.partner_id=="pid" and partner.user["partner_id"]=="pid" and repo.partners[0]["user_id"]=="uid"
    with pytest.raises(DuplicateEmail): run(service.register_partner({"email":"p@x.de"},None,"h","now"))

def test_service_authentication_all_lock_and_credential_paths():
    repo=Repo(); service=IdentityAccessService(repo)
    repo.attempt={"count":5,"lockout_until":(NOW+timedelta(minutes=1)).isoformat()}
    with pytest.raises(LoginLocked): run(service.authenticate("a","p","ip",lambda a,b:True,NOW))
    repo.attempt={"count":5,"lockout_until":(NOW-timedelta(minutes=1)).isoformat()}
    with pytest.raises(InvalidCredentials): run(service.authenticate("a","p","ip",lambda a,b:True,NOW))
    assert len(repo.cleared)==1 and repo.failed[0]=="ip:a"
    repo.users["u"]={"_id":"u","email":"a","password_hash":"hash"}; repo.attempt=None
    assert run(service.authenticate("A","p","ip",lambda p,h:p=="p",NOW))["_id"]=="u"
    with pytest.raises(InvalidCredentials): run(service.authenticate("A","bad","ip",lambda p,h:p=="p",NOW))

def test_service_password_reset_user_lookup_and_errors():
    repo=Repo(); service=IdentityAccessService(repo)
    assert run(service.user("missing")) is None and run(service.user("raise")) is None
    assert run(service.begin_password_reset("none","t",NOW)) is None
    repo.users["u"]={"_id":"u","email":"a","name":"A","password_hash":"old"}
    assert run(service.begin_password_reset("A","token",NOW))["name"]=="A"
    run(service.reset_password("token","new",NOW)); assert repo.users["u"]["password_hash"]=="new" and repo.reset["used"]
    with pytest.raises(InvalidResetToken): run(service.reset_password("missing","h",NOW))
    repo.reset={"token":"old","expires_at":(NOW-timedelta(seconds=1)).isoformat(),"used":False,"user_id":"u"}
    with pytest.raises(ExpiredResetToken): run(service.reset_password("old","h",NOW))
    repo.reset={"token":"naive","expires_at":datetime(2026,8,25),"used":False,"user_id":"u"}
    run(service.reset_password("naive","h",NOW))


def test_service_profile_and_notification_updates_are_partial_and_nested():
    repo = Repo()
    repo.users["u"] = {"_id": "u", "name": "Old"}
    service = IdentityAccessService(repo)
    run(service.update_profile("u", {"name": "New", "city": "Berlin", "bio": None}))
    assert repo.users["u"]["name"] == "New"
    assert repo.users["u"]["profile.city"] == "Berlin"
    run(service.update_profile("u", {"name": None}))
    run(service.update_notification_preferences("u", {"email_on_step_enter": False}))
    assert repo.users["u"]["notification_preferences"] == {"email_on_step_enter": False}

class Cursor:
    def __init__(self,rows): self.rows=rows
    def sort(self,*args): return self
    async def to_list(self,n): return self.rows
class Collection:
    def __init__(self,row=None): self.row=row; self.calls=[]
    async def find_one(self,q): self.calls.append(("one",q)); return self.row
    async def insert_one(self,d): self.calls.append(("insert",d)); return SimpleNamespace(inserted_id="507f1f77bcf86cd799439011")
    async def update_one(self,*a,**k): self.calls.append(("update",a,k))
    async def update_many(self,*a): self.calls.append(("many",a))
    async def delete_one(self,*a): self.calls.append(("delete",a))
    async def insert_many(self,d): self.calls.append(("insert_many",d))
    def find(self,*a): return Cursor([{"_id":"s"}])

def test_mongo_repository_complete_account_boundary():
    users=Collection({"_id":"u"}); partners=Collection(); attempts=Collection({"count":1}); resets=Collection({"token":"t"})
    db=SimpleNamespace(users=users,partners=partners,steps=Collection(),user_progress=Collection(),login_attempts=attempts,password_reset_tokens=resets)
    repo=MongoIdentityRepository(db); valid="507f1f77bcf86cd799439011"
    assert run(repo.user_by_email("a"))=={"_id":"u"}; assert run(repo.insert_user({"x":1}))[0]==valid
    run(repo.update_user("bad",{})); run(repo.update_user(valid,{"x":1})); assert run(repo.steps("s"))==[{"_id":"s"}]
    run(repo.insert_progress([])); run(repo.insert_progress([{"x":1}])); assert run(repo.insert_partner({"x":1}))==valid
    assert run(repo.login_attempt("i"))=={"count":1}; run(repo.record_failed_login("i","u")); run(repo.clear_login_attempt("i"))
    run(repo.consume_reset_tokens("u")); run(repo.insert_reset_token({"token":"t"})); assert run(repo.reset_token("t"))=={"token":"t"}
    run(repo.mark_reset_token_used("t"))

def test_account_error_mapping_is_specific_and_safe():
    assert account_http_error(DuplicateEmail()).detail=="Email already registered"
    assert account_http_error(LoginLocked()).status_code==429
    assert account_http_error(InvalidCredentials()).status_code==401
    assert account_http_error(InvalidResetToken()).detail=="Invalid or expired token"
    assert account_http_error(ExpiredResetToken()).detail=="Token expired"
    assert account_http_error(RuntimeError()).detail=="Invalid account operation"
