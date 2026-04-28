"""
Regression tests for the step-flow bug reported by user:

  "Wenn ich im ersten partner_selection einen Partner wähle und dieser den
   milestone freigibt, wird mir als User sofort 'Übersicht Fachsprachenprüfung'
   angezeigt. Das sollte aber wie im ersten Teil zu erst ein Entscheidungsfeld
   sein (selber hochladen/ partner wählen)."

Root-cause: Milestone steps (5, 9, 13, 17, 20, 24) had no `hide` condition, so
they were always visible in the timeline. After partner completes milestone #5,
the next visible step in the timeline was #9 (milestone Fachsprachenprüfung)
because steps #7 (upload) and #8 (partner_selection) are both hidden while
decision #6 is empty — the user therefore saw the milestone instead of the
expected decision step.

Fix: Each milestone now carries a `hide if decision-step's `decision` field is
empty` condition. The upload / partner_selection step has to be triggered first
by making a decision before the milestone is re-revealed.

These tests cover:
  1. Fresh user → milestone 9 is hidden until decision 6 is made.
  2. Partner completes milestone 5 → user sees step 6 (decision), NOT step 9.
  3. Covers ALL blocks: Antragstellung (5), Fachsprachen (9), Gleichwertigkeit
     (13), Kenntnisprüfung (17), Jobangebote (20), Weiterbildung (24).
  4. Upload path: decision=upload → milestone visible once upload step exists.
  5. Partner path: decision=partner → milestone visible once decision is set.
  6. Multi-partner block (Jobangebote) also respects hide-when-decision-empty.
  7. Evaluator fix: `field: 'decision'`, `operator: 'empty'` returns True when
     data.decision is absent (even if status is in_progress).
"""
import os
import time
import pytest
import requests


BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = BASE + "/api"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def step_maps(admin_token):
    steps = requests.get(f"{API}/admin/steps", headers={"Authorization": f"Bearer {admin_token}"}).json()
    return {
        "steps": steps,
        "id2order": {s["id"]: s["order"] for s in steps},
        "order2id": {s["order"]: s["id"] for s in steps},
        "order2type": {s["order"]: s["step_type"] for s in steps},
    }


@pytest.fixture()
def fresh_user():
    """Create + return (user_id, token, email) for a brand-new user.
    Each test gets its own user to avoid cross-contamination."""
    email = f"flowbug-{int(time.time() * 1000)}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "Flow1234!", "name": "Flow Bug"})
    r.raise_for_status()
    return r.json()["id"], r.json()["access_token"], email


@pytest.fixture()
def partner_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "partner-example@chrizz1001.de", "password": "Partner123!"})
    r.raise_for_status()
    return r.json()["access_token"]


# ---------- helpers ----------
def _complete_stammdaten(user_token, order2id):
    return requests.put(f"{API}/steps/progress",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={
                            "step_id": order2id[1], "status": "completed",
                            "data": {
                                "first_name": "Flow", "name": "Bug",
                                "date_of_birth": "1990-01-01",
                                "phone": "+49", "address": "Test 1",
                                "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
                                "anerkennungsverfahren_bundesland": "Berlin",
                                "fachrichtung_praktiziert": "Innere Medizin",
                                "fachrichtung_gewuenscht": "Innere Medizin",
                                "field_of_study": "Innere Medizin",
                            }
                        })


def _visibility(user_token):
    return requests.get(f"{API}/steps/visibility",
                        headers={"Authorization": f"Bearer {user_token}"}).json()


def _hidden_orders(vis, id2order):
    return set(id2order[sid] for sid in vis.get("hidden_step_ids", []) if sid in id2order)


def _set_decision(user_token, order2id, decision_order, value):
    return requests.put(f"{API}/steps/progress",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={"step_id": order2id[decision_order],
                              "status": "completed", "data": {"decision": value}})


# ---------- 1. Milestones hidden until decision is made ----------
class TestMilestoneHiddenUntilDecision:
    """All milestone steps must stay HIDDEN in the timeline until their
    corresponding decision step has a non-empty `decision` value."""

    # (milestone_order, decision_order)
    BLOCKS = [(5, 2), (9, 6), (13, 10), (17, 14), (20, 18), (24, 21)]

    def test_fresh_user_all_milestones_hidden(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _complete_stammdaten(tok, step_maps["order2id"])
        vis = _visibility(tok)
        hidden = _hidden_orders(vis, step_maps["id2order"])
        for ms, dec in self.BLOCKS:
            assert ms in hidden, (
                f"Milestone #{ms} should be HIDDEN while decision #{dec} is empty, "
                f"but hidden set is {sorted(hidden)}"
            )

    @pytest.mark.parametrize("milestone_order,decision_order", BLOCKS)
    def test_milestone_becomes_visible_after_decision(self, fresh_user, step_maps,
                                                      milestone_order, decision_order):
        """When the decision step is completed with any non-empty value, the
        corresponding milestone must become visible (even before work starts)."""
        _, tok, _ = fresh_user
        _complete_stammdaten(tok, step_maps["order2id"])

        # Satisfy prerequisite decisions so the block under test is unblocked.
        # We walk chronologically and set all prior decisions to 'upload' (the
        # simplest path — upload step is hidden until we actually upload).
        for ms, dec in self.BLOCKS:
            if ms >= milestone_order:
                break
            # Fast-forward: mark prior milestones as completed via admin so
            # block conditions (status_not completed on step 5 etc.) don't bite.
            _set_decision(tok, step_maps["order2id"], dec, "upload")

        vis_before = _visibility(tok)
        hidden_before = _hidden_orders(vis_before, step_maps["id2order"])
        assert milestone_order in hidden_before, \
            f"Milestone #{milestone_order} should still be hidden before decision #{decision_order}"

        # Now set the decision under test.
        _set_decision(tok, step_maps["order2id"], decision_order, "upload")

        vis_after = _visibility(tok)
        hidden_after = _hidden_orders(vis_after, step_maps["id2order"])
        assert milestone_order not in hidden_after, (
            f"Milestone #{milestone_order} should be VISIBLE after decision "
            f"#{decision_order} is filled, but hidden set is {sorted(hidden_after)}"
        )


# ---------- 2. The reported bug scenario (partner completes #5 → user sees #6, not #9) ----------
class TestPartnerCompletesMilestone:
    def test_user_sees_decision_not_next_milestone(self, fresh_user, step_maps, partner_token):
        user_id, user_tok, _ = fresh_user
        order2id = step_maps["order2id"]
        id2order = step_maps["id2order"]

        # Full path: stammdaten → decision=partner → pick partner → partner completes #5
        _complete_stammdaten(user_tok, order2id)
        _set_decision(user_tok, order2id, 2, "partner")
        partners = requests.get(f"{API}/partners", params={"tag": "Antragstellung Approbation"}).json()
        ils = next((p for p in partners if "ILS" in p["name"]), partners[0])
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": ils["id"], "data": {}})
        # Frontend writes step 4 progress in addition to the submission — mirror it
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[4], "status": "completed",
                           "data": {"selected_partner_id": ils["id"],
                                    "selected_partner_name": ils["name"]}})

        # Partner completes milestone #5
        r = requests.put(f"{API}/partner/users/{user_id}/progress",
                         headers={"Authorization": f"Bearer {partner_token}"},
                         json={"step_id": order2id[5], "status": "completed", "data": {}})
        assert r.status_code == 200

        # Visible order the USER sees on the dashboard
        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        visible_orders = sorted(
            s["order"] for s in step_maps["steps"] if s["id"] not in vis["hidden_step_ids"]
        )

        # Expected visible: 1, 2, 4, 5, 6 (+ future decision-only steps 10/14/18/21).
        # MUST NOT contain 9 (milestone Fachsprachen) — that's the bug.
        assert 6 in visible_orders, "Decision step #6 must be visible"
        assert 9 not in visible_orders, (
            f"BUG REGRESSION: milestone #9 (Übersicht Fachsprachenprüfung) "
            f"leaked into the visible timeline before decision #6 was made. "
            f"Visible: {visible_orders}"
        )

        # The first non-completed visible step must be #6 (decision), not #9 (milestone)
        prog = requests.get(f"{API}/steps/progress",
                            headers={"Authorization": f"Bearer {user_tok}"}).json()
        pm = {p["step_id"]: p for p in prog}
        sorted_steps = sorted(step_maps["steps"], key=lambda s: s["order"])
        visible = [s for s in sorted_steps if s["id"] not in vis["hidden_step_ids"]]
        first_todo = next(s for s in visible if pm.get(s["id"], {}).get("status") != "completed")
        assert first_todo["order"] == 6, (
            f"First non-completed visible step must be decision #6, got "
            f"#{first_todo['order']} [{first_todo['step_type']}] '{first_todo['title']}'"
        )
        assert first_todo["step_type"] == "decision"

    def test_chaining_multiple_blocks_does_not_leak_future_milestones(
        self, fresh_user, step_maps, partner_token
    ):
        """After the user completes decision + partner_selection + partner completes
        milestone in Block 2 (Fachsprachen), Block 3's milestone (Gleichwertigkeit,
        #13) must remain hidden — decision #10 is still empty."""
        user_id, user_tok, _ = fresh_user
        order2id = step_maps["order2id"]
        id2order = step_maps["id2order"]

        _complete_stammdaten(user_tok, order2id)
        # Block 1: upload path, simulate completed
        _set_decision(user_tok, order2id, 2, "upload")
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[3], "status": "completed",
                           "data": {"documents": [{"file_id": "f1", "filename": "x.pdf"}]}})
        # Block 2: decision=partner
        _set_decision(user_tok, order2id, 6, "partner")
        partners = requests.get(f"{API}/partners", params={"tag": "Fachsprachenprüfung"}).json() or \
                   requests.get(f"{API}/partners").json()
        p = partners[0]
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": p["id"], "data": {"step_order": 8}})
        requests.put(f"{API}/partner/users/{user_id}/progress",
                     headers={"Authorization": f"Bearer {partner_token}"},
                     json={"step_id": order2id[9], "status": "completed", "data": {}})

        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        assert 13 in hidden, "Milestone #13 should stay hidden — decision #10 is empty"
        assert 17 in hidden, "Milestone #17 should stay hidden — decision #14 is empty"
        assert 20 in hidden, "Milestone #20 should stay hidden — decision #18 is empty"
        assert 24 in hidden, "Milestone #24 should stay hidden — decision #21 is empty"


# ---------- 3. The evaluator fix: `empty` operator on a missing data field ----------
class TestEmptyOperatorOnMissingField:
    """Regression for the helper change in `_evaluate_condition`:
    `field: 'decision', operator: 'empty'` must return TRUE when data.decision
    is absent (previously it fell back to status and returned False).
    This is covered implicitly by the tests above, but we also verify it
    directly via the visibility endpoint response shape."""

    def test_decision_step_in_progress_still_reports_milestone_hidden(
        self, fresh_user, step_maps, partner_token
    ):
        """Specifically: partner_of_step_5 completes #5 which sets #6 to
        in_progress (NOT pending). The milestone #9 must still be hidden
        because data.decision is absent — the bug was: old evaluator fell back
        to status 'in_progress' which is never empty."""
        user_id, user_tok, _ = fresh_user
        order2id = step_maps["order2id"]
        id2order = step_maps["id2order"]

        _complete_stammdaten(user_tok, order2id)
        _set_decision(user_tok, order2id, 2, "partner")
        ils = requests.get(f"{API}/partners").json()[0]
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": ils["id"], "data": {}})
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[4], "status": "completed",
                           "data": {"selected_partner_id": ils["id"]}})
        requests.put(f"{API}/partner/users/{user_id}/progress",
                     headers={"Authorization": f"Bearer {partner_token}"},
                     json={"step_id": order2id[5], "status": "completed", "data": {}})

        # Step 6 is now in_progress (server sets next step on milestone completion)
        prog = requests.get(f"{API}/steps/progress",
                            headers={"Authorization": f"Bearer {user_tok}"}).json()
        step6 = next(p for p in prog if p["step_id"] == order2id[6])
        assert step6["status"] == "in_progress"
        assert not step6.get("data"), f"data should be empty, got {step6.get('data')}"

        # THE critical assertion — milestone #9 must still be hidden
        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        assert 9 in hidden, (
            "Milestone #9 leaked into visible timeline while step #6 is "
            "in_progress with empty data — the `empty` operator fallback bug"
        )


# ---------- 4. Multi-partner Jobangebote block (no upload) ----------
class TestJobangeboteMultiPartner:
    """Jobangebote has multi-partner selection (step 19) and no upload step.
    Milestone #20 should hide while decision #18 is empty, just like the others."""

    def test_jobangebote_milestone_hidden_until_decision(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _complete_stammdaten(tok, step_maps["order2id"])
        vis = _visibility(tok)
        hidden = _hidden_orders(vis, step_maps["id2order"])
        assert 20 in hidden, "Milestone #20 (Jobangebote) must be hidden before decision #18"

    def test_jobangebote_milestone_visible_after_decision(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _complete_stammdaten(tok, step_maps["order2id"])
        # Fast-forward all prior decisions so #18 becomes reachable
        for dec in (2, 6, 10, 14):
            _set_decision(tok, step_maps["order2id"], dec, "upload")
        _set_decision(tok, step_maps["order2id"], 18, "partner")
        vis = _visibility(tok)
        hidden = _hidden_orders(vis, step_maps["id2order"])
        assert 20 not in hidden, \
            f"Milestone #20 should be visible after decision #18, hidden: {sorted(hidden)}"


# ---------- 5. Sanity: hide conditions are present on all milestones ----------
def test_all_milestones_have_hide_when_decision_empty_condition(admin_token):
    """Guards against someone re-seeding without the new hide condition."""
    steps = requests.get(f"{API}/admin/steps",
                         headers={"Authorization": f"Bearer {admin_token}"}).json()
    expected = {5: 2, 9: 6, 13: 10, 17: 14, 20: 18, 24: 21}
    for ms_order, dec_order in expected.items():
        ms = next(s for s in steps if s["order"] == ms_order)
        assert ms["step_type"] == "milestone"
        matching = [c for c in ms.get("conditions", [])
                    if c.get("action") == "hide"
                    and c.get("source_step_order") == dec_order
                    and c.get("field") == "decision"
                    and c.get("operator") == "empty"]
        assert matching, (
            f"Milestone #{ms_order} ('{ms['title']}') missing hide-when-decision-"
            f"#{dec_order}-empty condition. Got conditions: {ms.get('conditions')}"
        )
