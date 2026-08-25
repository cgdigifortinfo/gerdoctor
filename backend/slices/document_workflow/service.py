"""Application service for document workflow state and editability."""
from __future__ import annotations

from slices.document_workflow.domain import resolve_document_workflow
from slices.document_workflow.models import DocumentWorkflowContext, WorkflowStepState
from slices.document_workflow.ports import DocumentWorkflowRepository


class DocumentWorkflowReadOnly(Exception):
    pass


class DocumentWorkflowService:
    def __init__(self, repository: DocumentWorkflowRepository) -> None:
        self._repository = repository

    @staticmethod
    def resolve(context: DocumentWorkflowContext) -> dict[str, WorkflowStepState]:
        return resolve_document_workflow(context)

    async def state(self, user_id: str, survey_id: str | None) -> dict[str, WorkflowStepState]:
        return self.resolve(await self._repository.load(user_id, survey_id))

    async def assert_editable(self, user_id: str, survey_id: str | None, step_id: str) -> None:
        step_state = (await self.state(user_id, survey_id)).get(step_id)
        if step_state is not None and step_state.read_only:
            raise DocumentWorkflowReadOnly(step_id)
