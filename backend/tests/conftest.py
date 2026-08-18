"""Shared pytest configuration for local, Docker, and CI execution."""

import os

import pytest
from dotenv import load_dotenv


load_dotenv("/app/frontend/.env")


@pytest.fixture(scope="session")
def base_url():
    """Backend URL without relying on a frontend file existing in the image."""
    return os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
