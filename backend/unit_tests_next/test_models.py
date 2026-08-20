"""Truth, failure, and boundary contracts for Pydantic request models."""

import math

import pytest
from pydantic import ValidationError

from models import (
    FlowPosition,
    PartnerBillingSettingsUpdate,
    PartnerCreate,
    PartnerRegister,
    StepCondition,
    StepCreate,
    StepFieldMapping,
    StepLayoutBulk,
    StepResponse,
)


class TestPartnerModels:
    def test_registration_accepts_minimal_valid_partner(self):
        model = PartnerRegister(
            company_name="Praxis GmbH",
            contact_name="Ada Arzt",
            email="ADA@Example.org",
            password="sicher123",
        )
        assert model.company_name == "Praxis GmbH"
        assert str(model.email).lower() == "ada@example.org"
        assert model.country == "DE"

    @pytest.mark.parametrize("field,value", [
        ("company_name", "x"),
        ("contact_name", "x"),
        ("email", "keine-email"),
        ("password", "short"),
        ("country", "DEU"),
    ])
    def test_registration_rejects_invalid_contract_fields(self, field, value):
        payload = {
            "company_name": "Praxis GmbH",
            "contact_name": "Ada Arzt",
            "email": "ada@example.org",
            "password": "sicher123",
            field: value,
        }
        with pytest.raises(ValidationError):
            PartnerRegister.model_validate(payload)

    def test_partner_create_turns_empty_contact_email_into_none(self):
        partner = PartnerCreate(name="Partner", description="", contact_email="")
        assert partner.contact_email is None

    @pytest.mark.parametrize("days", [0, 14, 365])
    def test_billing_payment_terms_accept_boundaries(self, days):
        assert PartnerBillingSettingsUpdate(payment_terms_days=days).payment_terms_days == days

    @pytest.mark.parametrize("payload", [
        {"payment_terms_days": -1},
        {"payment_terms_days": 366},
        {"default_currency": "EU"},
        {"default_currency": "EURO"},
    ])
    def test_billing_rejects_values_outside_contract(self, payload):
        with pytest.raises(ValidationError):
            PartnerBillingSettingsUpdate.model_validate(payload)


class TestStepModels:
    def test_recursive_condition_keeps_extension_fields(self):
        condition = StepCondition.model_validate({
            "action": "hide",
            "all_of": [
                {"source_step_order": 1, "field": "answer", "operator": "equals", "value": "yes"},
                {"source_step_order": 2, "operator": "status_is", "value": "completed"},
            ],
            "future_extension": {"enabled": True},
        })
        dumped = condition.model_dump(exclude_none=True)
        assert len(dumped["all_of"]) == 2
        assert dumped["future_extension"] == {"enabled": True}

    def test_condition_rejects_simultaneous_and_or_groups(self):
        with pytest.raises(ValidationError, match="both all_of and any_of"):
            StepCondition(all_of=[], any_of=[])

    @pytest.mark.parametrize("field,value", [
        ("source_step_order", 0),
        ("target_step_order", 0),
    ])
    def test_condition_rejects_non_positive_step_orders(self, field, value):
        with pytest.raises(ValidationError):
            StepCondition.model_validate({field: value})

    def test_field_mapping_requires_all_fields(self):
        with pytest.raises(ValidationError):
            StepFieldMapping(source_step_order=1, source_field="source")

    @pytest.mark.parametrize("coordinate", [math.nan, math.inf, -math.inf])
    def test_flow_position_rejects_non_finite_coordinates(self, coordinate):
        with pytest.raises(ValidationError):
            FlowPosition(x=coordinate, y=0)

    def test_flow_position_rejects_unknown_keys(self):
        with pytest.raises(ValidationError):
            FlowPosition.model_validate({"x": 1, "y": 2, "z": 3})

    def test_layout_validates_every_position(self):
        layout = StepLayoutBulk(positions={"step-a": {"x": 1.5, "y": -2}})
        assert layout.positions["step-a"].x == 1.5

    def test_step_response_ignores_database_only_fields(self):
        response = StepResponse.model_validate({
            "id": "step-a",
            "survey_id": "survey-a",
            "title": "Start",
            "description": "",
            "order": 1,
            "step_type": "form",
            "mongo_internal": True,
        })
        assert "mongo_internal" not in response.model_dump()

    def test_step_create_rejects_incomplete_mapping(self):
        with pytest.raises(ValidationError):
            StepCreate.model_validate({
                "title": "Target",
                "description": "",
                "order": 2,
                "step_type": "form",
                "field_mappings": [{"source_step_order": 1, "source_field": "name"}],
            })

