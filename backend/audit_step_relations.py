"""Audit Requirements, Conditions and mappings for one or more surveys."""

from __future__ import annotations

import argparse
import os

from pymongo import MongoClient
from slices.step_configuration.domain import condition_leaves, relation_issues


SYSTEM_FIELDS = {"status", "partner_uploads"}


def audit_steps(steps: list[dict]) -> list[str]:
    return [issue.text() for issue in relation_issues(steps)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surveys", nargs="+", default=["aerzte", "pflege"])
    args = parser.parse_args()
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = client[os.environ.get("DB_NAME", "test_database")]
    found = 0
    try:
        for slug in args.surveys:
            survey = database.surveys.find_one({"slug": slug})
            if not survey:
                print(f"{slug}: Survey fehlt")
                found += 1
                continue
            steps = list(database.steps.find({"survey_id": str(survey["_id"]), "is_active": {"$ne": False}}))
            issues = audit_steps(steps)
            found += len(issues)
            print(f"{slug}: {len(steps)} Steps, {len(issues)} Problem(e)")
            for issue in issues:
                print(f"  - {issue}")
    finally:
        client.close()
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
