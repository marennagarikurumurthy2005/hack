from datetime import date

from rest_framework import serializers

from .constants import (
    ACTIVITY_STATUS_COMPLETED,
    COMPLAINT_PRIORITIES,
    COMPLAINT_STATUSES,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    GOVERNMENT_ID_TYPES,
    IMAGE_UPLOAD_FOLDERS,
    PROGRESS_VISIBILITIES,
    PROJECT_ACTIVITY_STATUSES,
    PROJECT_MILESTONE_STATUSES,
    PROJECT_STATUSES,
    PROJECT_WORKFLOW_STAGES,
    ROLE_CITIZEN,
    ROLE_SUPER_ADMIN,
    ROLE_WARD_MEMBER,
    SCHEME_STATUSES,
    USER_ROLES,
    VERIFICATION_STATUSES,
)
from .utils import parse_list_input


class FlexibleListField(serializers.ListField):
    def to_internal_value(self, data):
        return super().to_internal_value(parse_list_input(data))


class RegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    mobile_number = serializers.RegexField(r"^\+?\d{10,15}$")
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    role = serializers.ChoiceField(choices=USER_ROLES, default=ROLE_CITIZEN)
    government_id_type = serializers.ChoiceField(choices=GOVERNMENT_ID_TYPES, required=False, allow_null=True)
    government_id_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    employee_id = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    department = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=150)
    designation = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=150)
    village = serializers.CharField(max_length=150)
    ward_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    district = serializers.CharField(max_length=150)
    state = serializers.CharField(max_length=150)
    pincode = serializers.RegexField(r"^\d{6}$")
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    identity_document = serializers.ImageField(required=False)

    def validate(self, attrs):
        role = attrs["role"]
        if role == ROLE_SUPER_ADMIN:
            raise serializers.ValidationError({"role": "Super admin accounts must be created by the platform owner."})

        attrs["email"] = attrs["email"].strip().lower()
        attrs["mobile_number"] = attrs["mobile_number"].strip()

        if role == ROLE_CITIZEN:
            if not attrs.get("government_id_type") or not attrs.get("government_id_number"):
                raise serializers.ValidationError(
                    {"government_id_number": "Citizens must provide a government-issued identity document."}
                )
        else:
            required_employee_fields = ("employee_id", "department", "designation")
            missing = [field for field in required_employee_fields if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(
                    {field: "This field is required for employee, ward member, and admin registrations." for field in missing}
                )
        return attrs


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)


class UserVerificationSerializer(serializers.Serializer):
    verification_status = serializers.ChoiceField(choices=VERIFICATION_STATUSES)
    review_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=USER_ROLES)


class ComplaintCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=120)
    description = serializers.CharField()
    priority = serializers.ChoiceField(choices=COMPLAINT_PRIORITIES, default="medium")
    village = serializers.CharField(max_length=150)
    ward_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    district = serializers.CharField(max_length=150)
    state = serializers.CharField(max_length=150)
    pincode = serializers.RegexField(r"^\d{6}$")
    address_line1 = serializers.CharField(max_length=255)
    address_line2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=7)


class ComplaintUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=200)
    category = serializers.CharField(required=False, max_length=120)
    description = serializers.CharField(required=False)
    priority = serializers.ChoiceField(required=False, choices=COMPLAINT_PRIORITIES)
    status = serializers.ChoiceField(required=False, choices=COMPLAINT_STATUSES)
    resolution_summary = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    village = serializers.CharField(required=False, max_length=150)
    ward_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    district = serializers.CharField(required=False, max_length=150)
    state = serializers.CharField(required=False, max_length=150)
    pincode = serializers.RegexField(required=False, regex=r"^\d{6}$")
    address_line1 = serializers.CharField(required=False, max_length=255)
    address_line2 = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    latitude = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=7)


class ComplaintAssignSerializer(serializers.Serializer):
    assigned_to = serializers.CharField()
    assignment_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ComplaintProgressSerializer(serializers.Serializer):
    message = serializers.CharField()
    status = serializers.ChoiceField(required=False, choices=COMPLAINT_STATUSES)
    progress_percent = serializers.IntegerField(required=False, min_value=0, max_value=100)
    visibility = serializers.ChoiceField(choices=PROGRESS_VISIBILITIES, default="public")


class SchemeSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    summary = serializers.CharField(max_length=500)
    description = serializers.CharField()
    department = serializers.CharField(max_length=150)
    status = serializers.ChoiceField(choices=SCHEME_STATUSES, default="published")
    eligibility = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    application_process = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    required_documents = FlexibleListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    village_tags = FlexibleListField(
        child=serializers.CharField(max_length=150),
        required=False,
        allow_empty=True,
    )
    contact_person = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=150)
    contact_phone = serializers.RegexField(required=False, regex=r"^\+?\d{10,15}$")
    contact_email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    office_address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    application_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    banner_image = serializers.ImageField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if isinstance(start_date, date) and isinstance(end_date, date) and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return attrs


class GenericImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    folder = serializers.ChoiceField(choices=IMAGE_UPLOAD_FOLDERS, default="general")


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    summary = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)
    description = serializers.CharField()
    category = serializers.CharField(max_length=120)
    priority = serializers.ChoiceField(choices=COMPLAINT_PRIORITIES, default="medium")
    status = serializers.ChoiceField(choices=PROJECT_STATUSES, default="planned")
    workflow_stage = serializers.ChoiceField(choices=PROJECT_WORKFLOW_STAGES, default="planning")
    villages = FlexibleListField(child=serializers.CharField(max_length=150), allow_empty=False)
    district = serializers.CharField(max_length=150)
    state = serializers.CharField(max_length=150)
    start_date = serializers.DateField(required=False, allow_null=True)
    target_end_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    owner_user_id = serializers.CharField()
    responsible_user_ids = FlexibleListField(
        child=serializers.CharField(max_length=64),
        required=False,
        allow_empty=True,
    )
    budget_allocated_amount = serializers.DecimalField(required=False, max_digits=14, decimal_places=2, default=0)
    budget_currency = serializers.CharField(required=False, max_length=10, default="INR")
    budget_allocations = FlexibleListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )
    tags = FlexibleListField(child=serializers.CharField(max_length=100), required=False, allow_empty=True)
    target_beneficiaries = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        target_end_date = attrs.get("target_end_date")
        end_date = attrs.get("end_date")
        if start_date and target_end_date and target_end_date < start_date:
            raise serializers.ValidationError({"target_end_date": "Target end date cannot be earlier than start date."})
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return attrs


class ProjectUpdateSerializer(ProjectCreateSerializer):
    name = serializers.CharField(required=False, max_length=200)
    description = serializers.CharField(required=False)
    category = serializers.CharField(required=False, max_length=120)
    priority = serializers.ChoiceField(required=False, choices=COMPLAINT_PRIORITIES)
    status = serializers.ChoiceField(required=False, choices=PROJECT_STATUSES)
    workflow_stage = serializers.ChoiceField(required=False, choices=PROJECT_WORKFLOW_STAGES)
    villages = FlexibleListField(child=serializers.CharField(max_length=150), required=False, allow_empty=False)
    district = serializers.CharField(required=False, max_length=150)
    state = serializers.CharField(required=False, max_length=150)
    owner_user_id = serializers.CharField(required=False)
    budget_allocated_amount = serializers.DecimalField(required=False, max_digits=14, decimal_places=2)
    budget_currency = serializers.CharField(required=False, max_length=10)


class ProjectActivityCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.ChoiceField(choices=PROJECT_ACTIVITY_STATUSES, default="not_started")
    assigned_to_user_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    priority = serializers.ChoiceField(choices=COMPLAINT_PRIORITIES, default="medium")
    dependency_ids = FlexibleListField(
        child=serializers.CharField(max_length=64),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})
        return attrs


class ProjectActivityUpdateSerializer(ProjectActivityCreateSerializer):
    title = serializers.CharField(required=False, max_length=200)
    status = serializers.ChoiceField(required=False, choices=PROJECT_ACTIVITY_STATUSES)
    priority = serializers.ChoiceField(required=False, choices=COMPLAINT_PRIORITIES)


class ProjectMilestoneCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    target_date = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=PROJECT_MILESTONE_STATUSES, default="pending")
    weight_percent = serializers.IntegerField(required=False, min_value=0, max_value=100, default=0)


class ProjectMilestoneUpdateSerializer(ProjectMilestoneCreateSerializer):
    title = serializers.CharField(required=False, max_length=200)
    status = serializers.ChoiceField(required=False, choices=PROJECT_MILESTONE_STATUSES)


class ProjectProgressCreateSerializer(serializers.Serializer):
    message = serializers.CharField()
    progress_percent = serializers.IntegerField(required=False, min_value=0, max_value=100)
    status = serializers.ChoiceField(required=False, choices=PROJECT_STATUSES)
    workflow_stage = serializers.ChoiceField(required=False, choices=PROJECT_WORKFLOW_STAGES)
    risk_level = serializers.ChoiceField(required=False, choices=COMPLAINT_PRIORITIES)


class ProjectBudgetUpdateSerializer(serializers.Serializer):
    allocated_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField(required=False, max_length=10, default="INR")
    allocations = FlexibleListField(child=serializers.DictField(), required=False, allow_empty=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ProjectExpenditureCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    category = serializers.CharField(max_length=120)
    description = serializers.CharField()
    spent_on = serializers.DateField(required=False, allow_null=True)
    vendor = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=150)
    receipt_reference = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=150)
    approved_by_user_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CitizenFeedbackCreateSerializer(serializers.Serializer):
    feedback_type = serializers.ChoiceField(choices=FEEDBACK_TYPES)
    subject = serializers.CharField(max_length=200)
    message = serializers.CharField()
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=120)
    village = serializers.CharField(max_length=150)
    ward_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    district = serializers.CharField(max_length=150)
    state = serializers.CharField(max_length=150)
    is_public = serializers.BooleanField(required=False, default=True)


class CitizenFeedbackUpdateSerializer(serializers.Serializer):
    subject = serializers.CharField(required=False, max_length=200)
    message = serializers.CharField(required=False)
    category = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=120)
    status = serializers.ChoiceField(required=False, choices=FEEDBACK_STATUSES)
    is_public = serializers.BooleanField(required=False)


class CitizenFeedbackRespondSerializer(serializers.Serializer):
    response_message = serializers.CharField()
    status = serializers.ChoiceField(choices=FEEDBACK_STATUSES, default="responded")
