from __future__ import annotations

import pytest

from slices.partner_selection.domain import (
    EmptyPartnerSelection,
    InvalidSelectionStep,
    MultipleSelectionRequired,
    PartnerNotOffered,
    PartnerSelectionError,
    PartnerUnavailable,
    SelectionSurveyMismatch,
)
from slices.partner_selection.web_errors import partner_selection_http_exception
from slices.partner_selection.web_serializers import public_partner_detail, public_partner_summary
from slices.partner_billing.web import INVOICE_FIELDS, invoice_view


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (InvalidSelectionStep("s"), 400, "Submission step is invalid or belongs to another survey"),
        (SelectionSurveyMismatch("s"), 400, "Submission step is invalid or belongs to another survey"),
        (MultipleSelectionRequired("s"), 400, "Multiple partners require a multi-selection step"),
        (EmptyPartnerSelection(), 422, "At least one partner must be selected"),
        (PartnerUnavailable("p"), 404, "Partner not found or inactive"),
        (PartnerNotOffered("p"), 400, "Partner is not offered in this selection step"),
    ],
)
def test_selection_errors_are_mapped_to_stable_http_contracts(error, status, detail) -> None:
    result = partner_selection_http_exception(error)
    assert (result.status_code, result.detail) == (status, detail)


def test_unknown_selection_error_is_rejected_explicitly() -> None:
    with pytest.raises(TypeError, match="Unsupported partner-selection error: PartnerSelectionError"):
        partner_selection_http_exception(PartnerSelectionError())


def test_public_partner_serializers_normalize_optional_and_unsafe_shapes() -> None:
    source = {
        "_id": 12, "name": "Partner", "description": "Description", "logo_url": "logo",
        "website": "site", "category": "medical", "tags": ["one"], "contact_email": "mail",
    }
    assert public_partner_summary(source) == {
        "id": "12", "name": "Partner", "description": "Description", "logo_url": "logo",
        "website": "site", "category": "medical", "tags": ["one"],
    }
    assert public_partner_detail(source)["contact_email"] == "mail"
    assert public_partner_summary({"id": "fallback", "tags": "invalid"}) == {
        "id": "fallback", "name": "", "description": "", "logo_url": None,
        "website": None, "category": None, "tags": [],
    }
    assert public_partner_detail({}) == {
        "id": "", "name": "", "description": "", "logo_url": None,
        "website": None, "category": None, "tags": [], "contact_email": None,
    }


def test_invoice_serializer_uses_an_explicit_allow_list() -> None:
    source = {"id": "in_1", "status": "paid", "secret": "hidden"}
    assert invoice_view(source) == {key: source.get(key) for key in INVOICE_FIELDS}
    assert "secret" not in invoice_view(source)
