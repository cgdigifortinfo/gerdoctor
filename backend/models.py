"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import List, Optional, Any


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str

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
    name: str
    field_type: str
    label: str
    placeholder: Optional[str] = None
    required: bool = False
    options: Optional[List[str]] = None

class StepCreate(BaseModel):
    title: str
    description: str
    order: int
    step_type: str
    fields: Optional[List[StepFieldCreate]] = None
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

class StepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    step_type: Optional[str] = None
    fields: Optional[List[StepFieldCreate]] = None
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

class StepReorder(BaseModel):
    step_ids: List[str]

class UserProgressUpdate(BaseModel):
    step_id: str
    status: str
    data: Optional[dict] = None

class PartnerSubmissionCreate(BaseModel):
    partner_id: str
    data: dict

class MultiPartnerSubmission(BaseModel):
    partner_ids: List[str]

class CMSContentUpdate(BaseModel):
    section: str
    content: dict

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

class SiteSettingsUpdate(BaseModel):
    site_title: Optional[str] = None
    logo_text: Optional[str] = None
    logo_bold_part: Optional[str] = None
    logo_light_part: Optional[str] = None
    contact_email: Optional[str] = None
    footer_text: Optional[str] = None
    primary_color: Optional[str] = None
    meta_description: Optional[str] = None
