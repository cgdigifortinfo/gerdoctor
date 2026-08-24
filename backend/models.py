"""Pydantic models for request/response validation.

Nested models intentionally allow additional keys where survey configuration is
extensible. This keeps old MongoDB documents readable while validating the
stable fields consumed by the application.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, model_validator
from typing import List, Optional, Any, Dict


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    survey_slug: Optional[str] = None


class PartnerRegister(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8)
    website: Optional[str] = None
    description: Optional[str] = ""
    country: str = Field(default="DE", min_length=2, max_length=2)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    created_at: Optional[str] = None

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    date_of_birth: Optional[str] = None
    profile_image_id: Optional[str] = None

class PartnerCreate(BaseModel):
    name: str
    description: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    linked_user_ids: Optional[List[str]] = None
    survey_ids: Optional[List[str]] = None
    step_user_fee_cents: Optional[Dict[str, int]] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_status: Optional[str] = None

    @field_validator('contact_email', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

    @field_validator('step_user_fee_cents')
    @classmethod
    def non_negative_step_prices(cls, value):
        if value and any(amount < 0 for amount in value.values()):
            raise ValueError('step prices cannot be negative')
        return value

class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    linked_user_ids: Optional[List[str]] = None
    survey_ids: Optional[List[str]] = None
    step_user_fee_cents: Optional[Dict[str, int]] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_status: Optional[str] = None

    @field_validator('contact_email', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

    @field_validator('step_user_fee_cents')
    @classmethod
    def non_negative_step_prices(cls, value):
        if value and any(amount < 0 for amount in value.values()):
            raise ValueError('step prices cannot be negative')
        return value

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

class EventConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    handlers: Optional[List[dict]] = None

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

class CMSContentUpdate(BaseModel):
    section: Optional[str] = None  # derived from URL path
    content: dict
    translations: Optional[dict] = None

class NotificationPreferences(BaseModel):
    email_on_step_enter: bool = True
    email_on_step_edit: bool = False
    email_on_step_leave: bool = True

class BulkRoleUpdate(BaseModel):
    user_ids: List[str]
    role: str

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "user"
    partner_id: Optional[str] = None
    survey_id: Optional[str] = None
    group_ids: Optional[List[str]] = None

class PermissionGroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    role: str = "user"
    permissions: List[str] = Field(default_factory=list)

class PermissionGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None

class UserPermissionsUpdate(BaseModel):
    group_ids: List[str] = Field(default_factory=list)
    allow: List[str] = Field(default_factory=list)
    deny: List[str] = Field(default_factory=list)

class SiteSettingsUpdate(BaseModel):
    site_title: Optional[str] = None
    logo_text: Optional[str] = None
    logo_bold_part: Optional[str] = None
    logo_light_part: Optional[str] = None
    contact_email: Optional[str] = None
    footer_text: Optional[str] = None
    primary_color: Optional[str] = None
    meta_description: Optional[str] = None
    # UI element feature-flags — phase-1 of the upcoming rights system.
    # Default `True` in the frontend when the key is absent.
    ui_show_journey_indicator: Optional[bool] = None
    ui_show_eta_header: Optional[bool] = None
    ui_show_progress_percentage: Optional[bool] = None
    stripe_sandbox_mode: Optional[bool] = None
    stripe_test_publishable_key: Optional[str] = None
    stripe_test_secret_key: Optional[str] = None
    stripe_test_webhook_secret: Optional[str] = None
    stripe_live_publishable_key: Optional[str] = None
    stripe_live_secret_key: Optional[str] = None
    stripe_live_webhook_secret: Optional[str] = None
    stripe_partner_price_id: Optional[str] = None
    stripe_partner_user_fee_cents: Optional[int] = Field(default=None, ge=0)
    stripe_partner_user_fee_currency: Optional[str] = None
    stripe_partner_payment_mode: Optional[str] = None
    stripe_automatic_tax: Optional[bool] = None
    stripe_allow_promotion_codes: Optional[bool] = None

class StepTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    config: dict  # full step config (title, description, step_type, fields, conditions, ...)

class StepTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None

class SurveyCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = ""
    audience: Optional[str] = ""
    is_active: bool = True
    is_default: bool = False
    theme: Optional[dict] = None

class SurveyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    audience: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    theme: Optional[dict] = None
