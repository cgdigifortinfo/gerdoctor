"""Stripe webhook signature verification adapter."""
from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Callable
from typing import Any


class StripeWebhookConfigurationError(RuntimeError): pass
class StripeWebhookSignatureError(ValueError): pass


def verified_stripe_event(
    body: bytes, signature: str, secret: str,
    now_timestamp: Callable[[], float], tolerance_seconds: int = 300,
) -> dict[str, Any]:
    if not secret:
        raise StripeWebhookConfigurationError
    parts: dict[str, str] = {}
    for item in signature.split(","):
        pair = item.split("=")
        if len(pair) == 2:
            parts[pair[0]] = pair[1]
    timestamp = parts.get("t")
    supplied = parts.get("v1")
    if not timestamp or not supplied:
        raise StripeWebhookSignatureError
    try:
        current_delta = abs(now_timestamp() - int(timestamp))
    except ValueError as error:
        raise StripeWebhookSignatureError from error
    if current_delta > tolerance_seconds:
        raise StripeWebhookSignatureError
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, supplied):
        raise StripeWebhookSignatureError
    event = json.loads(body)
    if not isinstance(event, dict):
        raise StripeWebhookSignatureError
    return event
