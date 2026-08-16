"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Any


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    survey_slug: Optional[str] = None

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

    @field_validator('contact_email', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

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

    @field_validator('contact_email', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v

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

class StepCreate(BaseModel):
    title: str
    description: str
    order: int
    step_type: str
    survey_id: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
    form_schema_version: int = 1
    filter_tag: Optional[str] = None
    skippable: bool = False
    skip_label: Optional[str] = None
    action_label: Optional[str] = None
    pending_message: Optional[str] = None
    complete_message: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_uploads: Optional[List[str]] = None
    field_mappings: Optional[List[dict]] = None
    conditions: Optional[List[dict]] = None
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
    flow_position: Optional[dict] = None  # {x, y}

class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    step_type: Optional[str] = None
    survey_id: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
    form_schema_version: Optional[int] = None
    filter_tag: Optional[str] = None
    skippable: Optional[bool] = None
    skip_label: Optional[str] = None
    action_label: Optional[str] = None
    pending_message: Optional[str] = None
    complete_message: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_uploads: Optional[List[str]] = None
    field_mappings: Optional[List[dict]] = None
    conditions: Optional[List[dict]] = None
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
    flow_position: Optional[dict] = None  # {x, y}

class StepLayoutBulk(BaseModel):
    positions: dict  # {step_id: {x, y}}

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
