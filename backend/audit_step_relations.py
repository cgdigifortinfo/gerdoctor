"""Audit Requirements, Conditions and mappings for one or more surveys."""

from __future__ import annotations

import argparse
import os

from pymongo import MongoClient


SYSTEM_FIELDS = {"status", "partner_uploads"}


def condition_leaves(condition: dict):
    children = condition.get("all_of") or condition.get("any_of")
    if children is not None:
        for child in children:
            yield from condition_leaves(child)
    else:
        yield condition


def audit_steps(steps: list[dict]) -> list[str]:
    issues: list[str] = []
    by_order = {step.get("order"): step for step in steps}
    if len(by_order) != len(steps):
        issues.append("Doppelte Step-Reihenfolge vorhanden")
    for step in steps:
        prefix = f"#{step.get('order')} {step.get('title')}"
        fields = {field.get("name"): field for field in step.get("fields", [])}
        for required in step.get("required_fields", []) or []:
            if required not in fields:
                issues.append(f"{prefix}: Requirement verweist auf unbekanntes Feld {required!r}")
        upload_options = {
            str(option.get("value", option.get("label", "")) if isinstance(option, dict) else option)
            for field in fields.values() if field.get("field_type") == "multiupload"
            for option in field.get("options", [])
        }
        for required in step.get("required_uploads", []) or []:
            if required not in upload_options:
                issues.append(f"{prefix}: Upload-Requirement {required!r} ist keine Dokumentoption")
        for root in step.get("conditions", []) or []:
            for condition in condition_leaves(root):
                source = by_order.get(condition.get("source_step_order"))
                if not source:
                    issues.append(f"{prefix}: Condition verweist auf fehlenden Source-Step #{condition.get('source_step_order')}")
                    continue
                field = condition.get("field")
                source_fields = {item.get("name") for item in source.get("fields", [])} | SYSTEM_FIELDS
                if field and field not in source_fields:
                    issues.append(f"{prefix}: Condition verweist auf unbekanntes Feld {field!r} in Step #{source.get('order')}")
                target = condition.get("target_step_order")
                if condition.get("action") == "redirect" and target not in by_order:
                    issues.append(f"{prefix}: Redirect-Ziel #{target} fehlt")
        for mapping in step.get("field_mappings", []) or []:
            source = by_order.get(mapping.get("source_step_order"))
            if not source or mapping.get("source_field") not in {field.get("name") for field in source.get("fields", [])}:
                issues.append(f"{prefix}: Field-Mapping hat keine plausible Quelle")
            if mapping.get("target_field") not in fields:
                issues.append(f"{prefix}: Field-Mapping hat kein plausibles Zielfeld")
    return issues


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
