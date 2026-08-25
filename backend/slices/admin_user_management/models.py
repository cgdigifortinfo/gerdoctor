"""Immutable admin-user commands and results."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    email: str
    password: str
    name: str
    role: str
    partner_id: str | None = None
    survey_id: str | None = None
    group_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CreatedUser:
    id: str
    survey_id: str | None
    survey_slug: str | None

    def to_document(self) -> dict[str, str | None]:
        return {"id": self.id, "survey_id": self.survey_id,
                "survey_slug": self.survey_slug, "message": "User created"}
