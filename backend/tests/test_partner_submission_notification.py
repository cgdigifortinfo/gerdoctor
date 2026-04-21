"""
Regression test: Partner receives a Mailgun notification when a user submits.

This runs the notify helper directly (no HTTP endpoint), monkey-patching the
SMTP `send_email_sync` so no real mail is sent. Verifies:
  1. notify_partner_of_new_submission sends to every role=partner user linked
     to the partner org + the partner's contact_email (deduplicated).
  2. notification_prefs.email=False opts a partner user out.
  3. The HTML body mentions the user name + fachrichtung + bundesland.

Run: cd /app && python3 backend/tests/test_partner_submission_notification.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Ensure helpers has SMTP credentials so the function tries to send
os.environ.setdefault("MAILGUN_SMTP_USER", "test-user")
os.environ.setdefault("MAILGUN_FROM_EMAIL", "noreply@gerdoctor.example.com")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import helpers  # noqa: E402


async def main() -> int:
    failures: list[str] = []
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    # The helpers module binds `db` internally — make sure our `db` matches
    helpers.db = db

    # ---- Capture email sends ----
    sent: list[tuple[str, str, str]] = []

    def fake_send(to_email, subject, html):
        sent.append((to_email, subject, html))
        return {"status": "success"}

    original = helpers.send_email_sync
    helpers.send_email_sync = fake_send
    try:
        # Pick a partner that has at least one partner-role user linked
        # Candidate: digiFORT Experts
        partner = await db.partners.find_one({"name": "digiFORT Experts"})
        if not partner:
            print("!! digiFORT Experts partner missing — skipping")
            return 0

        # Fake user dict (mimics the shape used in the real submit endpoint)
        user = {"_id": "fake-user-id", "email": "e2e-notify@gerdoctor.example.com",
                "name": "E2E Notify"}
        submission_data = {
            "fachrichtung_gewuenscht": "Innere Medizin",
            "anerkennungsverfahren_bundesland": "Berlin",
            "step_order": 4,
        }

        # ---- Case 1: basic send covers partner users + contact_email ----
        sent.clear()
        n = await helpers.notify_partner_of_new_submission(partner, user, submission_data)
        if n == 0:
            failures.append("no recipients reached for digiFORT Experts")

        # Verify recipient set = union of (contact_email, linked partner-role users)
        expected = set()
        if partner.get("contact_email"):
            expected.add(partner["contact_email"])
        pid = str(partner["_id"])
        async for pu in db.users.find({"role": "partner", "partner_id": pid}, {"email": 1}):
            if pu.get("email"):
                expected.add(pu["email"])
        actual = {to for to, _, _ in sent}
        missing = expected - actual
        extras = actual - expected
        if missing:
            failures.append(f"missing recipients: {missing}")
        if extras:
            failures.append(f"unexpected recipients: {extras}")
        if len(actual) != len(sent):
            failures.append(f"duplicates in send list: {sent}")
        print(f"  ✓ Case 1: notified {n} recipient(s) = {actual}")

        # ---- Case 2: body mentions user name + field + bundesland ----
        body = sent[0][2] if sent else ""
        for needle in (user["name"], "Innere Medizin", "Berlin", "digiFORT"):
            if needle not in body:
                failures.append(f"notification body missing '{needle}'")
        if not failures:
            print(f"  ✓ Case 2: body contains user name, field, bundesland, partner name")

        # ---- Case 3: opt-out via notification_prefs.email=False ----
        # Temporarily flip one partner user's prefs
        pu_sample = await db.users.find_one({"role": "partner", "partner_id": pid})
        if pu_sample:
            original_prefs = pu_sample.get("notification_prefs")
            await db.users.update_one(
                {"_id": pu_sample["_id"]},
                {"$set": {"notification_prefs": {"email": False}}},
            )
            sent.clear()
            await helpers.notify_partner_of_new_submission(partner, user, submission_data)
            recipients_after = {to for to, _, _ in sent}
            if pu_sample["email"] in recipients_after:
                failures.append(f"opted-out user {pu_sample['email']} still got an email")
            else:
                print(f"  ✓ Case 3: opt-out honored for {pu_sample['email']}")
            # Restore
            await db.users.update_one(
                {"_id": pu_sample["_id"]},
                {"$set": {"notification_prefs": original_prefs or {"email": True, "in_app": True}}},
            )
    finally:
        helpers.send_email_sync = original
        client.close()

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
