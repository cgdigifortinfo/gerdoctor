#!/usr/bin/env python3
"""Manually run the idempotent survey form-builder field migration."""
import asyncio

from database import db
from slices.step_configuration.form_builder import migrate_database_form_configs


async def main():
    updated = await migrate_database_form_configs(db)
    print(f"Form-builder migration complete: {updated} step(s) updated")


if __name__ == "__main__":
    asyncio.run(main())
