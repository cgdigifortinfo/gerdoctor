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
    email = f"flowtest-{int(time.time() * 1000)}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "Flow1234!", "name": "Flow Test"})
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


def _complete_schnellstart(user_token, order2id):
    """Pick 'selber' on the new Step 2 (Schnellstart) so the journey continues."""
    return requests.put(f"{API}/steps/progress",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={"step_id": order2id[2], "status": "completed",
                              "data": {"decision": "selber"}})


def _bootstrap(user_token, order2id):
    """Stammdaten + Schnellstart=selber so we can exercise downstream logic."""
    _complete_stammdaten(user_token, order2id)
    _complete_schnellstart(user_token, order2id)


def _set_decision(user_token, order2id, decision_order, value):
    return requests.put(f"{API}/steps/progress",
                        headers={"Authorization": f"Bearer {user_token}"},
                        json={"step_id": order2id[decision_order],
                              "status": "completed", "data": {"decision": value}})


# ---------- 1. Milestones hidden until decision is made ----------
class TestMilestoneHiddenUntilDecision:
    """All milestone steps must stay HIDDEN in the timeline until their
    corresponding decision step has a non-empty `decision` value."""

    # (milestone_order, decision_order) — orders shifted +1 after Schnellstart insertion
    BLOCKS = [(6, 3), (10, 7), (14, 11), (18, 15), (21, 19), (25, 22)]

    def test_fresh_user_all_milestones_hidden(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _bootstrap(tok, step_maps["order2id"])
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
        _bootstrap(tok, step_maps["order2id"])

        for ms, dec in self.BLOCKS:
            if ms >= milestone_order:
                break
            _set_decision(tok, step_maps["order2id"], dec, "upload")

        vis_before = _visibility(tok)
        hidden_before = _hidden_orders(vis_before, step_maps["id2order"])
        assert milestone_order in hidden_before, \
            f"Milestone #{milestone_order} should still be hidden before decision #{decision_order}"

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

        # Full path: stammdaten → schnellstart=selber → step3 decision=partner →
        # pick partner → partner completes milestone #6
        _bootstrap(user_tok, order2id)
        _set_decision(user_tok, order2id, 3, "partner")
        partners = requests.get(f"{API}/partners", params={"tag": "Antragstellung Approbation"}).json()
        ils = next((p for p in partners if "ILS" in p["name"]), partners[0])
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": ils["id"], "data": {}})
        # Frontend writes step 5 (partner_selection) progress in addition to the submission
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[5], "status": "completed",
                           "data": {"selected_partner_id": ils["id"],
                                    "selected_partner_name": ils["name"]}})

        # Partner completes milestone #6
        r = requests.put(f"{API}/partner/users/{user_id}/progress",
                         headers={"Authorization": f"Bearer {partner_token}"},
                         json={"step_id": order2id[6], "status": "completed", "data": {}})
        assert r.status_code == 200

        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        visible_orders = sorted(
            s["order"] for s in step_maps["steps"] if s["id"] not in vis["hidden_step_ids"]
        )

        # Expected visible: 1, 2, 3, 5, 6, 7. MUST NOT contain 10 (Fachsprache milestone).
        assert 7 in visible_orders, "Decision step #7 (Fachsprache) must be visible"
        assert 10 not in visible_orders, (
            f"BUG REGRESSION: milestone #10 (Übersicht Fachsprachenprüfung) "
            f"leaked into the visible timeline before decision #7 was made. "
            f"Visible: {visible_orders}"
        )

        # The first non-completed visible step must be #7 (decision), not #10 (milestone)
        prog = requests.get(f"{API}/steps/progress",
                            headers={"Authorization": f"Bearer {user_tok}"}).json()
        pm = {p["step_id"]: p for p in prog}
        sorted_steps = sorted(step_maps["steps"], key=lambda s: s["order"])
        visible = [s for s in sorted_steps if s["id"] not in vis["hidden_step_ids"]]
        first_todo = next(s for s in visible if pm.get(s["id"], {}).get("status") != "completed")
        assert first_todo["order"] == 7, (
            f"First non-completed visible step must be decision #7, got "
            f"#{first_todo['order']} [{first_todo['step_type']}] '{first_todo['title']}'"
        )
        assert first_todo["step_type"] == "decision"

    def test_chaining_multiple_blocks_does_not_leak_future_milestones(
        self, fresh_user, step_maps, partner_token
    ):
        """After the user completes block 1 + decision/partner_selection in
        block 2, milestones for blocks 3-6 must remain hidden."""
        user_id, user_tok, _ = fresh_user
        order2id = step_maps["order2id"]
        id2order = step_maps["id2order"]

        _bootstrap(user_tok, order2id)
        # Block 1 (Antragstellung): upload path
        _set_decision(user_tok, order2id, 3, "upload")
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[4], "status": "completed",
                           "data": {"documents": [{"file_id": "f1", "filename": "x.pdf"}]}})
        # Block 2 (Fachsprache): decision=partner
        _set_decision(user_tok, order2id, 7, "partner")
        partners = requests.get(f"{API}/partners", params={"tag": "Fachsprachenprüfung"}).json() or \
                   requests.get(f"{API}/partners").json()
        p = partners[0]
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": p["id"], "data": {"step_order": 9}})
        requests.put(f"{API}/partner/users/{user_id}/progress",
                     headers={"Authorization": f"Bearer {partner_token}"},
                     json={"step_id": order2id[10], "status": "completed", "data": {}})

        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        assert 14 in hidden, "Milestone #14 (Gleichwert.) should stay hidden — decision #11 is empty"
        assert 18 in hidden, "Milestone #18 (Kenntnis) should stay hidden — decision #15 is empty"
        assert 21 in hidden, "Milestone #21 (Jobangebote) should stay hidden — decision #19 is empty"
        assert 25 in hidden, "Milestone #25 (Weiterbildung) should stay hidden — decision #22 is empty"


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
        """Specifically: partner_of_step_6 completes #6 which sets #7 to
        in_progress (NOT pending). The milestone #10 must still be hidden
        because data.decision is absent — the bug was: old evaluator fell back
        to status 'in_progress' which is never empty."""
        user_id, user_tok, _ = fresh_user
        order2id = step_maps["order2id"]
        id2order = step_maps["id2order"]

        _bootstrap(user_tok, order2id)
        _set_decision(user_tok, order2id, 3, "partner")
        ils = requests.get(f"{API}/partners").json()[0]
        requests.post(f"{API}/partners/submit",
                      headers={"Authorization": f"Bearer {user_tok}"},
                      json={"partner_id": ils["id"], "data": {}})
        requests.put(f"{API}/steps/progress",
                     headers={"Authorization": f"Bearer {user_tok}"},
                     json={"step_id": order2id[5], "status": "completed",
                           "data": {"selected_partner_id": ils["id"]}})
        requests.put(f"{API}/partner/users/{user_id}/progress",
                     headers={"Authorization": f"Bearer {partner_token}"},
                     json={"step_id": order2id[6], "status": "completed", "data": {}})

        # Step 7 is now in_progress (server sets next step on milestone completion)
        prog = requests.get(f"{API}/steps/progress",
                            headers={"Authorization": f"Bearer {user_tok}"}).json()
        step7 = next(p for p in prog if p["step_id"] == order2id[7])
        assert step7["status"] == "in_progress"
        assert not step7.get("data"), f"data should be empty, got {step7.get('data')}"

        # THE critical assertion — milestone #10 must still be hidden
        vis = _visibility(user_tok)
        hidden = _hidden_orders(vis, id2order)
        assert 10 in hidden, (
            "Milestone #10 leaked into visible timeline while step #7 is "
            "in_progress with empty data — the `empty` operator fallback bug"
        )


# ---------- 4. Multi-partner Jobangebote block (no upload) ----------
class TestJobangeboteMultiPartner:
    """Jobangebote has multi-partner selection (step 20) and no upload step.
    Milestone #21 should hide while decision #19 is empty, just like the others."""

    def test_jobangebote_milestone_hidden_until_decision(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _bootstrap(tok, step_maps["order2id"])
        vis = _visibility(tok)
        hidden = _hidden_orders(vis, step_maps["id2order"])
        assert 21 in hidden, "Milestone #21 (Jobangebote) must be hidden before decision #19"

    def test_jobangebote_milestone_visible_after_decision(self, fresh_user, step_maps):
        _, tok, _ = fresh_user
        _bootstrap(tok, step_maps["order2id"])
        # Fast-forward all prior block decisions so #19 becomes reachable
        for dec in (3, 7, 11, 15):
            _set_decision(tok, step_maps["order2id"], dec, "upload")
        _set_decision(tok, step_maps["order2id"], 19, "partner")
        vis = _visibility(tok)
        hidden = _hidden_orders(vis, step_maps["id2order"])
        assert 21 not in hidden, \
            f"Milestone #21 should be visible after decision #19, hidden: {sorted(hidden)}"


# ---------- 5. Sanity: hide conditions are present on all milestones ----------
def test_all_milestones_have_hide_when_decision_empty_condition(admin_token):
    """Guards against someone re-seeding without the new hide condition."""
    steps = requests.get(f"{API}/admin/steps",
                         headers={"Authorization": f"Bearer {admin_token}"}).json()
    expected = {6: 3, 10: 7, 14: 11, 18: 15, 21: 19, 25: 22}
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
