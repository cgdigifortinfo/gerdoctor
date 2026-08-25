"""JWT encoding and decoding adapter."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping

import jwt

from infrastructure.clock import Clock


class IdentityTokenCodec:
    def __init__(self, secret: str, clock: Clock, algorithm: str = "HS256") -> None:
        self._secret, self._clock, self.algorithm = secret, clock, algorithm

    def access_token(self, user_id: str, email: str, role: str) -> str:
        return jwt.encode({"sub": user_id, "email": email, "role": role,
                           "exp": self._clock.now() + timedelta(hours=2), "type": "access"},
                          self._secret, algorithm=self.algorithm)

    def refresh_token(self, user_id: str) -> str:
        return jwt.encode({"sub": user_id, "exp": self._clock.now() + timedelta(days=7), "type": "refresh"},
                          self._secret, algorithm=self.algorithm)

    def decode(self, token: str) -> Mapping[str, Any]:
        return jwt.decode(token, self._secret, algorithms=[self.algorithm])
