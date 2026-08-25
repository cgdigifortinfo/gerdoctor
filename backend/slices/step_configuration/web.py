"""HTTP translation for Step Configuration errors."""
from fastapi import HTTPException

from slices.step_configuration.service import StepConfigurationNotFound


def step_configuration_http_error(error: StepConfigurationNotFound) -> HTTPException:
    return HTTPException(status_code=404, detail="Step not found")
