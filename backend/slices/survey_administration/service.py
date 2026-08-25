"""Survey administration application service."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from typing import Any
from slices.survey_administration.domain import (
    default_survey_document, normalized_slug, survey_document, survey_update, survey_view,
)
from slices.survey_administration.models import SurveyDraft
from slices.survey_administration.ports import SurveyAdministrationRepository

class SurveyNotFound(ValueError): pass
class SurveySlugRequired(ValueError): pass
class DuplicateSurveySlug(ValueError): pass

class SurveyAdministrationService:
    def __init__(self, repository: SurveyAdministrationRepository, now: Callable[[], str], default_slug: str) -> None:
        self._repo, self._now, self._default_slug = repository, now, default_slug
    async def list_surveys(self) -> list[dict[str, Any]]:
        return [survey_view(row) for row in await self._repo.surveys()]
    async def ensure_default(self) -> dict[str, Any]:
        survey = await self._repo.default_survey() or await self._repo.survey_by_slug(self._default_slug)
        if survey is None:
            _, survey = await self._repo.insert(default_survey_document(self._default_slug, self._now()))
        return survey
    async def by_slug(self, slug: str | None) -> dict[str, Any]:
        if not slug: return await self.ensure_default()
        survey = await self._repo.survey_by_slug(slug, active_only=True)
        if survey is None: raise SurveyNotFound
        return survey
    async def for_user(self, user: Mapping[str, Any], slug: str | None = None) -> dict[str, Any]:
        if slug: return await self.by_slug(slug)
        survey_id = user.get("survey_id")
        if survey_id:
            survey = await self._repo.survey(str(survey_id))
            if survey is not None: return survey
        return await self.ensure_default()
    async def create(self, draft: SurveyDraft) -> str:
        slug = normalized_slug(draft.slug)
        if not slug: raise SurveySlugRequired
        if await self._repo.duplicate_slug(slug): raise DuplicateSurveySlug
        if draft.is_default: await self._repo.clear_defaults()
        survey_id, _ = await self._repo.insert(survey_document(draft, self._now()))
        return survey_id
    async def update(self, survey_id: str, values: Mapping[str, Any]) -> list[str]:
        if await self._repo.survey(survey_id) is None: raise SurveyNotFound
        fields = survey_update(values, self._now())
        slug = fields.get("slug")
        if slug is not None:
            if not slug: raise SurveySlugRequired
            if await self._repo.duplicate_slug(str(slug), survey_id): raise DuplicateSurveySlug
        if fields.get("is_default"): await self._repo.clear_defaults(survey_id)
        await self._repo.update(survey_id, fields)
        return list(fields)
