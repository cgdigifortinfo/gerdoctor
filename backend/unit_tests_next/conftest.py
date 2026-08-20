"""Isolated fixtures for the candidate unit-test suite."""

import os


# Production modules read these values while importing. Unit tests never open a
# database connection, but deterministic placeholders keep imports hermetic.
os.environ.setdefault("MONGO_URL", "mongodb://unit-test.invalid:27017")
os.environ.setdefault("DB_NAME", "gerdoctor_unit_next")
os.environ.setdefault("JWT_SECRET", "unit-test-secret-with-sufficient-entropy")

