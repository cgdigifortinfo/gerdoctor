"""Fail CI unless mutmut executed and every generated mutant was killed."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(path: str = "mutants/mutmut-cicd-stats.json") -> int:
    stats = json.loads(Path(path).read_text(encoding="utf-8"))
    unacceptable = {
        key: stats.get(key, 0)
        for key in ("survived", "no_tests", "suspicious", "timeout", "segfault")
        if stats.get(key, 0)
    }
    total = int(stats.get("total", 0))
    killed = int(stats.get("killed", 0))
    if total <= 0 or killed != total or unacceptable:
        print(f"Mutation gate failed: total={total}, killed={killed}, problems={unacceptable}")
        return 1
    print(f"Mutation gate passed: {killed}/{total} mutants killed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
