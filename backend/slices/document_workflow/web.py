"""Translate document-workflow application errors to HTTP errors."""
from fastapi import HTTPException

from slices.document_workflow.service import DocumentWorkflowReadOnly


def document_workflow_http_error(error: DocumentWorkflowReadOnly) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="Dieser Schritt ist nach dem Dokumenten-Upload schreibgeschützt.",
    )
