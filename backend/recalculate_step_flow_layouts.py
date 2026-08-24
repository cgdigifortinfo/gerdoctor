"""Recalculate and persist the editor flow layout for configured surveys."""

from __future__ import annotations

import argparse
import os

from pymongo import MongoClient


X_STEP = 280
Y_CENTER = 140
LANE_GAP = 160


def calculate_positions(steps: list[dict]) -> dict[str, dict[str, float]]:
    ordered = sorted(steps, key=lambda step: step.get("order", 0))
    positions: dict[str, dict[str, float]] = {}
    x, index = 20, 0
    while index < len(ordered):
        step = ordered[index]
        branch_condition = next((condition for condition in step.get("conditions", []) if
            condition.get("action") == "hide"
            and condition.get("field") == "decision"
            and condition.get("operator") == "not_equals"
        ), None)
        if not branch_condition:
            positions[str(step["_id"])] = {"x": x, "y": Y_CENTER}
            x += X_STEP
            index += 1
            continue
        decision_order = branch_condition.get("source_step_order")
        branches: list[tuple[dict, dict]] = []
        while index < len(ordered):
            candidate = ordered[index]
            condition = next((item for item in candidate.get("conditions", []) if
                item.get("action") == "hide"
                and item.get("source_step_order") == decision_order
                and item.get("field") == "decision"
                and item.get("operator") == "not_equals"
            ), None)
            if not condition:
                break
            branches.append((candidate, condition))
            index += 1
        branches.sort(key=lambda item: str(item[1].get("value", "")))
        for lane, (candidate, _) in enumerate(branches):
            offset = (lane - (len(branches) - 1) / 2) * LANE_GAP
            positions[str(candidate["_id"])] = {"x": x, "y": Y_CENTER + offset}
        x += X_STEP
    return positions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Persist positions instead of only printing them")
    parser.add_argument("--surveys", nargs="+", default=["aerzte", "pflege"])
    args = parser.parse_args()
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = client[os.environ.get("DB_NAME", "test_database")]
    try:
        for slug in args.surveys:
            survey = database.surveys.find_one({"slug": slug})
            if not survey:
                raise RuntimeError(f"Survey nicht gefunden: {slug}")
            steps = list(database.steps.find({"survey_id": str(survey["_id"]), "is_active": {"$ne": False}}))
            positions = calculate_positions(steps)
            if args.apply:
                for step_id, position in positions.items():
                    database.steps.update_one({"_id": next(step["_id"] for step in steps if str(step["_id"]) == step_id)}, {"$set": {"flow_position": position}})
            print(f"{slug}: {len(positions)} Positionen {'gespeichert' if args.apply else 'berechnet'}")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
