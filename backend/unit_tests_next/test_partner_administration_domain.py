from bson import ObjectId

from slices.partner_administration.domain import (
    create_partner_document, partner_admin_record, partner_update_plan,
    service_steps_for_partner, sorted_partner_records, user_role_update,
)


def test_create_document_distinguishes_omitted_and_empty_surveys():
    base = {"name": "Partner", "description": "Description"}
    omitted = create_partner_document(base, "now")
    empty = create_partner_document({**base, "survey_ids": [], "billing_status": "paid"}, "now")
    assert omitted["is_active"] is True and omitted["billing_status"] == "pending"
    assert empty["is_active"] is False and empty["billing_status"] == "paid"
    assert omitted["registration_source"] == "admin" and omitted["created_at"] == "now"
    populated = create_partner_document({
        "name": "P", "description": "D", "logo_url": "logo", "website": "web",
        "contact_email": "mail", "category": "cat", "tags": ["tag"],
        "linked_user_ids": ["u"], "survey_ids": ["s"], "step_user_fee_cents": {"step": 7},
        "stripe_customer_id": "cus", "stripe_subscription_id": "sub", "billing_status": "active",
    }, "created")
    assert populated == {
        "name": "P", "description": "D", "logo_url": "logo", "website": "web",
        "contact_email": "mail", "category": "cat", "tags": ["tag"], "linked_user_ids": ["u"],
        "survey_ids": ["s"], "step_user_fee_cents": {"step": 7}, "stripe_customer_id": "cus",
        "stripe_subscription_id": "sub", "billing_status": "active", "is_active": True,
        "registration_status": "active", "registration_source": "admin", "created_at": "created",
    }


def test_update_plan_deduplicates_surveys_and_derives_access():
    plan = partner_update_plan({
        "name": "New", "description": None, "linked_user_ids": ["u"],
        "survey_ids": ["s", "s"], "step_user_fee_cents": {"step": 100},
        "billing_status": "trialing",
    }, "now")
    assert plan.survey_ids == ("s",) and plan.priced_step_ids == ("step",)
    assert plan.fields == {
        "name": "New", "survey_ids": ["s"], "step_user_fee_cents": {"step": 100},
        "billing_status": "trialing", "updated_at": "now", "linked_user_ids": ["u"],
        "is_active": True, "registration_status": "active", "access_unlocked": True,
    }
    empty = partner_update_plan({"survey_ids": [], "billing_status": "past_due"}, "later")
    assert empty.fields["registration_status"] == "pending" and empty.fields["access_unlocked"] is False
    untouched = partner_update_plan({}, "now")
    assert untouched.survey_ids is None and untouched.priced_step_ids is None


def test_partner_record_filters_steps_and_preserves_admin_fallbacks():
    partner_id = ObjectId()
    partner = {"_id": partner_id, "name": "Beta", "tags": ["language"], "survey_ids": ["survey"], "is_active": False}
    steps = [
        {"_id": ObjectId(), "title": "Offered", "order": 2, "filter_tag": "language", "survey_id": "survey", "partner_user_fee_cents": 500},
        {"_id": ObjectId(), "filter_tag": "other", "survey_id": "survey"},
        {"_id": ObjectId(), "filter_tag": "language", "survey_id": "other"},
    ]
    offered = service_steps_for_partner(partner, steps)
    record = partner_admin_record(partner, [{"id": "u"}], 4, offered)
    assert [step["title"] for step in offered] == ["Offered"]
    assert record["id"] == str(partner_id) and record["registration_status"] == "pending"
    assert record["linked_users"] == [{"id": "u"}] and record["pending_registrations"] == 4
    assert record == {
        "id": str(partner_id), "name": "Beta", "description": "", "logo_url": None,
        "website": None, "contact_email": None, "category": None, "tags": ["language"],
        "is_active": False, "user_id": None, "linked_users": [{"id": "u"}],
        "linked_user_ids": [], "pending_registrations": 4, "survey_ids": ["survey"],
        "registration_status": "pending", "registration_source": "admin", "registered_at": None,
        "stripe_account_id": None, "stripe_onboarding_complete": False, "stripe_customer_id": "",
        "stripe_subscription_id": "", "billing_status": "", "step_user_fee_cents": {},
        "service_steps": offered,
    }
    assert offered == [{
        "id": str(steps[0]["_id"]), "title": "Offered", "order": 2, "survey_id": "survey",
        "filter_tag": "language", "step_user_fee_cents": 500,
    }]
    unrestricted = service_steps_for_partner({"tags": ["language"]}, steps)
    assert len(unrestricted) == 2
    minimal_step = {"_id": "minimal", "filter_tag": "language"}
    assert service_steps_for_partner({"tags": ["language"]}, [minimal_step]) == [{
        "id": "minimal", "title": "", "order": 0, "survey_id": None,
        "filter_tag": "language", "step_user_fee_cents": None,
    }]
    assert service_steps_for_partner({"tags": [None]}, [{"_id": "legacy"}]) == [{
        "id": "legacy", "title": "", "order": 0, "survey_id": None,
        "filter_tag": "", "step_user_fee_cents": None,
    }]
    minimal = partner_admin_record({"_id": "p", "name": "Minimal"}, [], 0, [])
    assert minimal == {
        "id": "p", "name": "Minimal", "description": "", "logo_url": None, "website": None,
        "contact_email": None, "category": None, "tags": [], "is_active": True, "user_id": None,
        "linked_users": [], "linked_user_ids": [], "pending_registrations": 0, "survey_ids": [],
        "registration_status": "active", "registration_source": "admin", "registered_at": None,
        "stripe_account_id": None, "stripe_onboarding_complete": False, "stripe_customer_id": "",
        "stripe_subscription_id": "", "billing_status": "", "step_user_fee_cents": {},
        "service_steps": [],
    }
    enriched_partner = {
        "_id": "rich", "name": "Rich", "description": "D", "logo_url": "L", "website": "W",
        "contact_email": "E", "category": "C", "tags": ["T"], "is_active": True,
        "user_id": "U", "linked_user_ids": ["U"], "survey_ids": ["S"],
        "registration_status": "custom", "registration_source": "self", "registered_at": "R",
        "created_at": "C", "stripe_account_id": "A", "stripe_onboarding_complete": True,
        "stripe_customer_id": "CUS", "stripe_subscription_id": "SUB", "billing_status": "paid",
        "step_user_fee_cents": {"step": 1},
    }
    enriched = partner_admin_record(enriched_partner, [{"id": "U"}], 2, [{"id": "step"}])
    assert enriched == {
        "id": "rich", "name": "Rich", "description": "D", "logo_url": "L", "website": "W",
        "contact_email": "E", "category": "C", "tags": ["T"], "is_active": True,
        "user_id": "U", "linked_users": [{"id": "U"}], "linked_user_ids": ["U"],
        "pending_registrations": 2, "survey_ids": ["S"], "registration_status": "custom",
        "registration_source": "self", "registered_at": "R", "stripe_account_id": "A",
        "stripe_onboarding_complete": True, "stripe_customer_id": "CUS",
        "stripe_subscription_id": "SUB", "billing_status": "paid",
        "step_user_fee_cents": {"step": 1}, "service_steps": [{"id": "step"}],
    }
    created_fallback = partner_admin_record({"_id": "p", "name": "P", "created_at": "created"}, [], 0, [])
    assert created_fallback["registered_at"] == "created"


def test_sorting_and_role_updates_are_deterministic():
    records = [{"_id": "0", "name": "ä"}, {"_id": "1", "name": "Alpha"}, {"_id": "2"}]
    assert [row.get("name") for row in sorted_partner_records(records)] == [None, "Alpha", "ä"]
    tied = [{"_id": "2", "name": "Same"}, {"_id": "1", "name": "same"}]
    assert [row["_id"] for row in sorted_partner_records(tied)] == ["1", "2"]
    missing_id = [{"_id": "1", "name": "Same"}, {"name": "same"}]
    assert [row.get("_id") for row in sorted_partner_records(missing_id)] == [None, "1"]
    assert user_role_update("user", None) == {
        "role": "user", "group_ids": [], "permission_overrides": {"allow": [], "deny": []},
    }
    assert user_role_update("partner", "g", "p") == {
        "role": "partner", "group_ids": ["g"],
        "permission_overrides": {"allow": [], "deny": []}, "partner_id": "p",
    }
