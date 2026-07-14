import os
import uuid

import httpx
import pytest


API = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_user(email: str) -> tuple[str, str]:
    response = httpx.post(
        f"{API}/api/auth/register",
        json={"email": email, "password": "Test123!", "name": email.split("@")[0]},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["id"], payload["access_token"]


@pytest.fixture
def admin_token():
    response = httpx.post(
        f"{API}/api/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def test_file_download_is_limited_to_owner_or_admin(admin_token):
    run = uuid.uuid4().hex[:8]
    owner_id = other_id = None
    try:
        owner_id, owner_token = register_user(f"test_file_owner_{run}@chrizz1001.de")
        other_id, other_token = register_user(f"test_file_other_{run}@chrizz1001.de")

        upload = httpx.post(
            f"{API}/api/files/upload",
            headers=auth(owner_token),
            files={"file": ("nachweis.txt", b"secret", "text/plain")},
            timeout=15,
        )
        upload.raise_for_status()
        file_id = upload.json()["id"]

        owner_download = httpx.get(f"{API}/api/files/{file_id}", headers=auth(owner_token), timeout=15)
        assert owner_download.status_code == 200
        assert owner_download.content == b"secret"

        other_download = httpx.get(f"{API}/api/files/{file_id}", headers=auth(other_token), timeout=15)
        assert other_download.status_code == 403

        admin_download = httpx.get(f"{API}/api/files/{file_id}", headers=auth(admin_token), timeout=15)
        assert admin_download.status_code == 200
        assert admin_download.content == b"secret"
    finally:
        with httpx.Client(timeout=15) as client:
            for user_id in [owner_id, other_id]:
                if user_id:
                    client.delete(f"{API}/api/admin/users/{user_id}", headers=auth(admin_token))


def test_upload_rejects_unsupported_active_content(admin_token):
    response = httpx.post(
        f"{API}/api/files/upload",
        headers=auth(admin_token),
        files={"file": ("payload.html", b"<script>alert(1)</script>", "text/html")},
        timeout=15,
    )
    assert response.status_code == 400
