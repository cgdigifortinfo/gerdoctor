"""Backend tests for iteration 34: Partner self-service tags, Insights dashboard,
Match scoring via extended submissions/other-users, submissions excludes partner users."""
import os
import requests
import pytest
from pathlib import Path

def _load_env():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin@example.com", "Admin123!")


@pytest.fixture(scope="module")
def ils_partner():
    return _login("partner-example@chrizz1001.de", "Partner123!")


@pytest.fixture(scope="module")
def praxis_partner():
    return _login("empfang@chrizz1001.de", "Partner123!")


# ---------- Partner Profile (extended fields) ----------
def test_partner_profile_returns_extended_fields(ils_partner):
    r = ils_partner.get(f"{API}/partner/profile", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in ("partner_name", "description", "category", "tags", "logo_url"):
        assert k in data, f"missing field {k}: {data.keys()}"
    assert isinstance(data["tags"], list)
    # Expected ILS tags from review request
    assert any(t in data["tags"] for t in ["Berlin", "Kardiologie", "Innere Medizin", "Bayern"]), data["tags"]


def test_partner_update_partner_data_persists(ils_partner):
    # First read
    r0 = ils_partner.get(f"{API}/partner/profile", timeout=30)
    original_tags = r0.json().get("tags", [])
    original_desc = r0.json().get("description", "")
    original_name = r0.json().get("partner_name")
    original_cat = r0.json().get("category")

    # Update with new dedup + empty strip
    new_tags = original_tags + ["Berlin", "  NeuerTag  ", ""]
    new_desc = "Test description " + str(os.urandom(3).hex())
    r = ils_partner.put(
        f"{API}/partner/partner-data",
        json={"description": new_desc, "tags": new_tags},
        timeout=30,
    )
    assert r.status_code == 200, r.text

    r2 = ils_partner.get(f"{API}/partner/profile", timeout=30)
    data = r2.json()
    # Dedupe applied
    assert data["tags"].count("Berlin") == 1
    # Stripped and empty removed
    assert "NeuerTag" in data["tags"]
    assert "" not in data["tags"]
    # Description updated
    assert data["description"] == new_desc
    # Name/Category/Logo unchanged
    assert data["partner_name"] == original_name
    assert data["category"] == original_cat

    # Restore tags for downstream match tests
    restore = [t for t in data["tags"] if t != "NeuerTag"]
    if "Berlin" not in restore:
        restore.append("Berlin")
    ils_partner.put(
        f"{API}/partner/partner-data",
        json={"description": original_desc, "tags": restore},
        timeout=30,
    )


def test_partner_update_rejects_name_category_logo(ils_partner):
    # Send fields that should be ignored at the model level (name/category/logo not in PartnerSelfUpdate)
    r = ils_partner.put(
        f"{API}/partner/partner-data",
        json={"name": "HackedName", "category": "Hacked", "logo_url": "hacked.png", "description": "safe"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    r2 = ils_partner.get(f"{API}/partner/profile", timeout=30)
    data = r2.json()
    assert data["partner_name"] != "HackedName"
    assert data["category"] != "Hacked"
    assert data.get("logo_url") != "hacked.png"


# ---------- Insights ----------
def test_partner_insights_payload_shape(ils_partner):
    r = ils_partner.get(f"{API}/partner/insights", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    required = [
        "new_submissions_7d", "new_submissions_30d", "total_linked_users",
        "by_fachrichtung", "by_bundesland", "conversion_funnel",
        "conversion_rate_pct", "timeline_30d",
    ]
    for k in required:
        assert k in data, f"missing: {k}"
    assert isinstance(data["timeline_30d"], list) and len(data["timeline_30d"]) == 30
    for entry in data["timeline_30d"]:
        assert "date" in entry and "count" in entry
    funnel = data["conversion_funnel"]
    for k in ("received", "accepted", "completed"):
        assert k in funnel
    # total_linked_users must be > 0 for ILS
    assert data["total_linked_users"] >= 1, data
    # by_fachrichtung and by_bundesland entries shape
    for group in (data["by_fachrichtung"], data["by_bundesland"]):
        for e in group:
            assert "label" in e and "count" in e


# ---------- Submissions (bundesland + role filter) ----------
def test_submissions_include_bundesland_and_exclude_partner(ils_partner):
    r = ils_partner.get(f"{API}/partner/submissions", timeout=30)
    assert r.status_code == 200, r.text
    subs = r.json()
    assert isinstance(subs, list)
    assert len(subs) > 0
    for s in subs:
        assert "bundesland" in s, s
        assert "field_of_study" in s
    # Partner self (partner-example@chrizz1001.de) should NOT appear
    partner_emails = [s.get("user_email") for s in subs]
    assert "partner-example@chrizz1001.de" not in partner_emails, partner_emails


def test_other_users_include_bundesland(ils_partner):
    r = ils_partner.get(f"{API}/partner/other-users", timeout=30)
    assert r.status_code == 200, r.text
    others = r.json()
    assert isinstance(others, list)
    if others:
        assert "bundesland" in others[0]


# ---------- Match scoring (indirect: verify fields exist so FE can compute) ----------
def test_match_fields_present_for_ils(ils_partner):
    """The FE computes match via scoreUserForPartner(user, partnerTags). Validate that
    each submitted user has the data points (`bundesland`, `field_of_study`) the FE
    needs — picking any sample is enough; we don't depend on a specific user."""
    r = ils_partner.get(f"{API}/partner/submissions", timeout=30)
    subs = r.json()
    assert subs, "expected at least 1 submission for ILS"
    sample = next(
        (s for s in subs if s.get("bundesland") and s.get("field_of_study")),
        None,
    )
    assert sample is not None, f"no sub has both bundesland+field_of_study: {[(s.get('user_email'), s.get('bundesland'), s.get('field_of_study')) for s in subs[:5]]}"
    assert isinstance(sample["bundesland"], str) and sample["bundesland"]
    assert isinstance(sample["field_of_study"], str) and sample["field_of_study"]


def test_praxis_partner_profile_has_tags(praxis_partner):
    r = praxis_partner.get(f"{API}/partner/profile", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    # Expect at least some of the seeded tags
    expected = {"Bayern", "Allgemeinmedizin", "Jobangebote", "München", "Praxis"}
    overlap = expected & set(data.get("tags", []))
    assert len(overlap) >= 2, f"expected overlap with {expected}, got tags {data.get('tags')}"


def test_praxis_partner_insights(praxis_partner):
    r = praxis_partner.get(f"{API}/partner/insights", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "timeline_30d" in data and len(data["timeline_30d"]) == 30
