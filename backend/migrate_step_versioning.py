"""Run the idempotent Step/answer history migration manually."""
import asyncio
import json

from database import db, client
from slices.step_versioning.facade import migrate_step_answer_versioning


async def main():
    try:
        result = await migrate_step_answer_versioning(db)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
