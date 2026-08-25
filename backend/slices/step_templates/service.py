"""Application service for the complete step-template lifecycle."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from slices.step_templates.domain import (
    admin_actor, instantiated_step, step_source_config, template_document, template_update, template_view,
)
from slices.step_templates.models import AppliedTemplate, TemplateDraft
from slices.step_templates.ports import StepTemplateRepository

VersionStep = Callable[[Mapping[str, Any], Mapping[str, Any], list[Any], Mapping[str, Any], str], Awaitable[None]]
InsertVersion = Callable[[Mapping[str, Any], int, Mapping[str, Any], str], Awaitable[None]]
WriteProgress = Callable[[str, Mapping[str, Any], str, Mapping[str, Any], Mapping[str, Any], str], Awaitable[None]]

class TemplateNotFound(ValueError): pass
class SourceStepNotFound(ValueError): pass


class StepTemplateService:
    def __init__(self, repository: StepTemplateRepository, now: Callable[[], str],
                 version_step: VersionStep, insert_version: InsertVersion,
                 write_progress: WriteProgress) -> None:
        self._repo, self._now = repository, now
        self._version_step, self._insert_version, self._write_progress = version_step, insert_version, write_progress

    async def templates(self) -> list[dict[str, Any]]:
        return [template_view(item) for item in await self._repo.templates()]
    async def create(self, draft: TemplateDraft) -> str:
        return await self._repo.insert_template(template_document(draft.name, draft.description, draft.config, self._now()))
    async def update(self, template_id: str, values: Mapping[str, Any]) -> list[str]:
        fields = template_update(values, self._now()); await self._repo.update_template(template_id, fields)
        return list(fields)
    async def delete(self, template_id: str) -> str:
        template = await self._repo.template(template_id)
        if template is None: raise TemplateNotFound
        await self._repo.delete_template(template_id); return str(template.get("name", ""))
    async def create_from_step(self, step_id: str, name: str, description: str) -> str:
        step = await self._repo.step(step_id)
        if step is None: raise SourceStepNotFound
        return await self.create(TemplateDraft(name, description, step_source_config(step)))
    async def apply(self, template_id: str, survey_id: str, order: int,
                    admin: Mapping[str, Any]) -> AppliedTemplate:
        template = await self._repo.template(template_id)
        if template is None: raise TemplateNotFound
        actor = admin_actor(admin)
        for shifted in await self._repo.shifted_steps(survey_id, order):
            await self._version_step(shifted, {"order": shifted["order"] + 1}, [], actor, "template_reorder")
        step_id, step = await self._repo.insert_step(instantiated_step(template.get("config", {}), survey_id, order, self._now()))
        await self._insert_version(step, 1, actor, "template_create")
        for user_id in await self._repo.survey_user_ids(survey_id):
            await self._write_progress(user_id, step, "pending", {}, actor, "template_initial_progress")
        return AppliedTemplate(step_id, survey_id)
