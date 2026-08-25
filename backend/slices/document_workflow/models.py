"""Immutable document-workflow values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class WorkflowDocument:
    file_id: str
    filename: str
    document_type: str
    uploaded_by: str

    def as_dict(self) -> dict[str, str]:
        return {
            "file_id": self.file_id, "filename": self.filename,
            "document_type": self.document_type, "uploaded_by": self.uploaded_by,
        }


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    id: str
    order: float
    kind: str
    fields: tuple[Mapping[str, Any], ...]
    conditions: tuple[Mapping[str, Any], ...]
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkflowProgress:
    step_id: str
    status: str
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DocumentWorkflowContext:
    steps: tuple[WorkflowStep, ...]
    progress: tuple[WorkflowProgress, ...]


@dataclass(frozen=True, slots=True)
class WorkflowStepState:
    read_only: bool = False
    documents: tuple[WorkflowDocument, ...] = ()
    documents_pending: bool = False
    document_workflow: bool = False

    def as_dict(self) -> dict[str, Any]:
        if self.document_workflow:
            return {
                "documents": [item.as_dict() for item in self.documents],
                "documents_pending": self.documents_pending,
                "document_workflow": True,
            }
        return {"read_only": self.read_only}
