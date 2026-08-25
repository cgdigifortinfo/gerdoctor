"""Pydantic models for request/response validation.

Nested models intentionally allow additional keys where survey configuration is
extensible. This keeps old MongoDB documents readable while validating the
stable fields consumed by the application.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, model_validator
from typing import List, Optional, Any, Dict
from slices.identity_access.web import (
    ForgotPassword, NotificationPreferences, PartnerRegister, ProfileUpdate,
    ResetPassword, UserLogin, UserRegister,
)
from slices.partner_administration.web import PartnerCreate, PartnerUpdate


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    created_at: Optional[str] = None

class StepFieldCreate(BaseModel):
    id: Optional[str] = None
    name: str
    field_type: str
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[Any]] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    width: Optional[str] = "full"
    content: Optional[str] = None
    image_url: Optional[str] = None
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    heading_level: Optional[int] = None
    accept: Optional[str] = None
    multiple: Optional[bool] = None
    rows: Optional[int] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    validation_pattern: Optional[str] = None


class FlowPosition(BaseModel):
    """Canvas coordinates shared by React Flow and the layout API."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x: float
    y: float


class StepFieldMapping(BaseModel):
    """Copies a field value from an earlier step into the current step."""

    model_config = ConfigDict(extra="allow")
    source_step_order: int = Field(ge=1)
    source_field: str = Field(min_length=1)
    target_field: str = Field(min_length=1)


class StepCondition(BaseModel):
    """A leaf condition or recursive AND/OR condition group.

    Child conditions may inherit ``action`` from their parent, which is why the
    action is optional here. Unknown keys remain available for future operators.
    """

    model_config = ConfigDict(extra="allow")
    action: Optional[str] = None
    source_step_order: Optional[int] = Field(default=None, ge=1)
    field: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Any] = None
    target_step_order: Optional[int] = Field(default=None, ge=1)
    message: Optional[str] = None
    all_of: Optional[List["StepCondition"]] = None
    any_of: Optional[List["StepCondition"]] = None

    @model_validator(mode="after")
    def one_compound_operator(self):
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
    survey_id: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
    form_schema_version: int = 1
    filter_tag: Optional[str] = None
    partner_user_fee_cents: Optional[int] = Field(default=None, ge=0)
    skippable: bool = False
    skip_label: Optional[str] = None
    action_label: Optional[str] = None
    pending_message: Optional[str] = None
    complete_message: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_uploads: Optional[List[str]] = None
    field_mappings: Optional[List[StepFieldMapping]] = None
    conditions: Optional[List[StepCondition]] = None
    duration_value: int = 0
    duration_unit: str = "days"
    email_on_enter: bool = False
    email_on_edit: bool = False
    email_on_leave: bool = False
    email_subject_enter: Optional[str] = None
    email_body_enter: Optional[str] = None
    email_subject_edit: Optional[str] = None
    email_body_edit: Optional[str] = None
    email_subject_leave: Optional[str] = None
    email_body_leave: Optional[str] = None
    translations: Optional[dict] = None
    flow_position: Optional[FlowPosition] = None

class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    step_type: Optional[str] = None
    survey_id: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
    form_schema_version: Optional[int] = None
    filter_tag: Optional[str] = None
    partner_user_fee_cents: Optional[int] = Field(default=None, ge=0)
    skippable: Optional[bool] = None
    skip_label: Optional[str] = None
    action_label: Optional[str] = None
    pending_message: Optional[str] = None
    complete_message: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_uploads: Optional[List[str]] = None
    field_mappings: Optional[List[StepFieldMapping]] = None
    conditions: Optional[List[StepCondition]] = None
    duration_value: Optional[int] = None
    duration_unit: Optional[str] = None
    email_on_enter: Optional[bool] = None
    email_on_edit: Optional[bool] = None
    email_on_leave: Optional[bool] = None
    email_subject_enter: Optional[str] = None
    email_body_enter: Optional[str] = None
    email_subject_edit: Optional[str] = None
    email_body_edit: Optional[str] = None
    email_subject_leave: Optional[str] = None
    email_body_leave: Optional[str] = None
    is_active: Optional[bool] = None
    translations: Optional[dict] = None
    flow_position: Optional[FlowPosition] = None

class StepLayoutBulk(BaseModel):
    positions: Dict[str, FlowPosition]


class StepResponse(StepCreate):
    """Stable API representation returned by the admin step endpoints."""

    model_config = ConfigDict(extra="ignore")
    id: str
    survey_id: str = ""
    is_active: bool = True
    current_version: int = 1
    is_deleted: bool = False
    deleted_at: Optional[str] = None

class StepReorder(BaseModel):
    step_ids: List[str]
    survey_id: Optional[str] = None

class UserProgressUpdate(BaseModel):
    step_id: str
    status: str
    data: Optional[dict] = None

class PartnerStepAction(BaseModel):
    action: str
    reason: Optional[str] = None
    data: Optional[dict] = None

class PartnerSubmissionCreate(BaseModel):
    partner_id: str
    data: dict

class MultiPartnerSubmission(BaseModel):
    partner_ids: List[str]
    data: Optional[dict] = None

class PartnerSelfUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class PartnerBillingSettingsUpdate(BaseModel):
    legal_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    default_currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    invoice_footer: Optional[str] = None
    payment_terms_days: Optional[int] = Field(default=None, ge=0, le=365)
