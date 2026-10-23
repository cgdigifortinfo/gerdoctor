"""Database connection module."""
import os
from typing import Any
from motor.motor_asyncio import AsyncIOMotorClient

mongo_url = os.environ['MONGO_URL']
client: AsyncIOMotorClient[dict[str, Any]] = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
