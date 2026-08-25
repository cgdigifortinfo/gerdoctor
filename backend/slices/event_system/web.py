"""HTTP error mapping for event administration."""
from fastapi import HTTPException
from pydantic import BaseModel

from slices.event_system.domain import UnsupportedHandlerType
from slices.event_system.service import EventConfigNotFound, EventNotFound

class EventConfigUpdate(BaseModel):
    enabled: bool | None = None
    handlers: list[dict[str, object]] | None = None


def event_system_http_error(error: Exception) -> HTTPException:
    if isinstance(error, (EventNotFound, EventConfigNotFound)):
        return HTTPException(status_code=404, detail="Event not found" if isinstance(error, EventNotFound) else "Event type not found")
    if isinstance(error, UnsupportedHandlerType):
        return HTTPException(status_code=422, detail="Only email and notification handlers are currently supported")
    return HTTPException(status_code=400, detail="Invalid event operation")
