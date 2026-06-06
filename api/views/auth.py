from django.conf import settings
from pymongo.errors import DuplicateKeyError
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ..constants import ROLE_SUPER_ADMIN, VERIFICATION_APPROVED, VERIFICATION_PENDING
from ..permissions import IsAuthenticatedUser
from ..repositories import UserRepository
from ..responses import api_response
from ..serializers import LoginSerializer, PasswordChangeSerializer, RegistrationSerializer
from ..services.auth_service import (
    generate_access_token,
    hash_password,
    serialize_user_for_response,
    verify_password,
)
from ..services.media_service import upload_image
from ..utils import utc_now


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)

        if self.user_repository.find_by_email(validated_data["email"]):
            raise ValidationError({"email": "A user with this email already exists."})
        if self.user_repository.find_by_mobile_number(validated_data["mobile_number"]):
            raise ValidationError({"mobile_number": "A user with this mobile number already exists."})

        government_id_number = validated_data.get("government_id_number")
        if government_id_number and self.user_repository.find_by_government_id_number(government_id_number):
            raise ValidationError({"government_id_number": "This identity document is already registered."})

        employee_id = validated_data.get("employee_id")
        if employee_id and self.user_repository.find_by_employee_id(employee_id):
            raise ValidationError({"employee_id": "This employee ID is already registered."})

        password = validated_data.pop("password")
        identity_document = validated_data.pop("identity_document", None)
        if identity_document:
            validated_data["identity_document"] = upload_image(
                identity_document,
                "identity-documents",
                field_name="identity_document",
            )

        user_payload = {
            **validated_data,
            "password_hash": hash_password(password),
            "verification_status": VERIFICATION_PENDING,
            "review_notes": None,
            "verified_at": None,
            "verified_by": None,
            "last_login_at": None,
        }

        try:
            user = self.user_repository.create(user_payload)
        except DuplicateKeyError as exc:
            raise ValidationError({"detail": "A unique field already exists. Please review the registration data."}) from exc

        return api_response(
            data={"user": serialize_user_for_response(user, include_confidential=False)},
            message="Registration submitted successfully. Please wait for super admin approval before logging in.",
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"]
        password = serializer.validated_data["password"]

        user = self.user_repository.find_by_identifier(identifier)
        if not user or not verify_password(password, user["password_hash"]):
            raise AuthenticationFailed("Invalid email/username/mobile number or password.")

        verification_status = user.get("verification_status")
        if user.get("role") != ROLE_SUPER_ADMIN and verification_status != VERIFICATION_APPROVED:
            return api_response(
                data={"verification_status": verification_status},
                message=f"Your account is currently '{verification_status}'. Please wait for approval or contact support.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        self.user_repository.update_by_id(user["_id"], {"last_login_at": utc_now()})
        user = self.user_repository.find_by_id(user["_id"])
        access_token = generate_access_token(user)

        return api_response(
            data={
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in_minutes": settings.JWT_SETTINGS["ACCESS_TOKEN_LIFETIME_MINUTES"],
                "user": serialize_user_for_response(user, include_confidential=True),
            },
            message="Login successful.",
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def post(self, request):
        return api_response(message="Logout successful on the API. Discard the bearer token on the client side.")


class MeView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def get(self, request):
        user = self.user_repository.find_by_id(request.user.id)
        if not user:
            raise AuthenticationFailed("Authenticated user no longer exists.")
        return api_response(data={"user": serialize_user_for_response(user, include_confidential=True)})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.user_repository.find_by_id(request.user.id)
        if not user:
            raise AuthenticationFailed("Authenticated user no longer exists.")

        if not verify_password(serializer.validated_data["current_password"], user["password_hash"]):
            raise PermissionDenied("Current password is incorrect.")

        updated_user = self.user_repository.update_by_id(
            user["_id"],
            {"password_hash": hash_password(serializer.validated_data["new_password"])},
        )
        return api_response(
            data={"user": serialize_user_for_response(updated_user, include_confidential=True)},
            message="Password updated successfully.",
        )
