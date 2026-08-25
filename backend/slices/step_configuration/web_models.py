"""Validated HTTP models for administrative step configuration."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StepFieldCreate(BaseModel):
    id: str | None = None
    name: str
    field_type: str
    label: str
    placeholder: str | None = None
    required: bool = False
    options: list[Any] | None = None
    help_text: str | None = None
    default_value: Any | None = None
    width: str | None = "full"
    content: str | None = None
    image_url: str | None = None
    alt_text: str | None = None
    caption: str | None = None
    heading_level: int | None = None
    accept: str | None = None
    multiple: bool | None = None
    rows: int | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    validation_pattern: str | None = None


class FlowPosition(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float
    y: float


class StepFieldMapping(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_step_order: int = Field(ge=1)
    source_field: str = Field(min_length=1)
    target_field: str = Field(min_length=1)


class StepCondition(BaseModel):
    model_config = ConfigDict(extra="allow")
    action: str | None = None
    source_step_order: int | None = Field(default=None, ge=1)
    field: str | None = None
    operator: str | None = None
    value: Any | None = None
    target_step_order: int | None = Field(default=None, ge=1)
    message: str | None = None
    all_of: list["StepCondition"] | None = None
    any_of: list["StepCondition"] | None = None

    @model_validator(mode="after")
    def one_compound_operator(self) -> "StepCondition":
        if self.all_of is not None and self.any_of is not None:
            raise ValueError("condition cannot contain both all_of and any_of")
        if self.all_of is not None and not self.all_of:
            raise ValueError("all_of condition must contain at least one child")
        if self.any_of is not None and not self.any_of:
            raise ValueError("any_of condition must contain at least one child")
        return self


class StepCreate(BaseModel):
    title: str
    description: str
    order: int
    step_type: str
    survey_id: str | None = None
    fields: list[StepFieldCreate] | None = None
    form_schema_version: int = 1
    filter_tag: str | None = None
    partner_user_fee_cents: int | None = Field(default=None, ge=0)
    skippable: bool = False
    skip_label: str | None = None
    action_label: str | None = None
    pending_message: str | None = None
    complete_message: str | None = None
    required_fields: list[str] | None = None
    required_uploads: list[str] | None = None
    field_mappings: list[StepFieldMapping] | None = None
    conditions: list[StepCondition] | None = None
    duration_value: int = 0
    duration_unit: str = "days"
    email_on_enter: bool = False
    email_on_edit: bool = False
    email_on_leave: bool = False
    email_subject_enter: str | None = None
    email_body_enter: str | None = None
    email_subject_edit: str | None = None
    email_body_edit: str | None = None
    email_subject_leave: str | None = None
    email_body_leave: str | None = None
    translations: dict[str, Any] | None = None
    flow_position: FlowPosition | None = None


class StepUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    order: int | None = None
    step_type: str | None = None
    survey_id: str | None = None
    fields: list[StepFieldCreate] | None = None
    form_schema_version: int | None = None
    filter_tag: str | None = None
    partner_user_fee_cents: int | None = Field(default=None, ge=0)
    skippable: bool | None = None
    skip_label: str | None = None
    action_label: str | None = None
    pending_message: str | None = None
    complete_message: str | None = None
    required_fields: list[str] | None = None
    required_uploads: list[str] | None = None
    field_mappings: list[StepFieldMapping] | None = None
    conditions: list[StepCondition] | None = None
    duration_value: int | None = None
    duration_unit: str | None = None
    email_on_enter: bool | None = None
    email_on_edit: bool | None = None
    email_on_leave: bool | None = None
    email_subject_enter: str | None = None
    email_body_enter: str | None = None
    email_subject_edit: str | None = None
    email_body_edit: str | None = None
    email_subject_leave: str | None = None
    email_body_leave: str | None = None
    is_active: bool | None = None
    translations: dict[str, Any] | None = None
    flow_position: FlowPosition | None = None


class StepLayoutBulk(BaseModel):
    positions: dict[str, FlowPosition]


class StepResponse(StepCreate):
    model_config = ConfigDict(extra="ignore")
    id: str
    survey_id: str = ""
    is_active: bool = True
    current_version: int = 1
    is_deleted: bool = False
    deleted_at: str | None = None


class StepReorder(BaseModel):
    step_ids: list[str]
    survey_id: str | None = None
