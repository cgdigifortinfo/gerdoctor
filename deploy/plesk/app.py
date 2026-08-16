"""Production entrypoint serving the API and the compiled React application."""

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from server import app


FRONTEND_ROOT = Path("/app/frontend").resolve()


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    return {"status": "ok"}


@app.get("/{requested_path:path}", include_in_schema=False)
async def frontend(requested_path: str):
    """Serve compiled assets and fall back to index.html for React routes."""
    if requested_path == "api" or requested_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    candidate = (FRONTEND_ROOT / requested_path).resolve()
    if candidate.is_relative_to(FRONTEND_ROOT) and candidate.is_file():
        return FileResponse(candidate)

    return FileResponse(FRONTEND_ROOT / "index.html")
