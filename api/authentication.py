from dataclasses import dataclass

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .constants import ROLE_SUPER_ADMIN, VERIFICATION_APPROVED
from .repositories import UserRepository
from .services.auth_service import decode_access_token


@dataclass
class AuthenticatedUser:
    id: str
    full_name: str
    email: str
    role: str
    verification_status: str
    village: str | None = None
    district: str | None = None
    state: str | None = None
    mobile_number: str | None = None
    raw: dict | None = None

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def has_role(self, *roles: str) -> bool:
        return self.role == ROLE_SUPER_ADMIN or self.role in roles

    @classmethod
    def from_document(cls, document: dict):
        return cls(
            id=str(document["_id"]),
            full_name=document.get("full_name", ""),
            email=document.get("email", ""),
            role=document.get("role", ""),
            verification_status=document.get("verification_status", ""),
            village=document.get("village"),
            district=document.get("district"),
            state=document.get("state"),
            mobile_number=document.get("mobile_number"),
            raw=document,
        )


class JWTAuthentication(BaseAuthentication):
    keyword = "bearer"

    def __init__(self) -> None:
        self.user_repository = UserRepository()

    def authenticate(self, request):
        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            return None

        header_parts = authorization_header.split()
        if len(header_parts) != 2 or header_parts[0].strip().lower() != self.keyword:
            raise AuthenticationFailed("Authorization header must be in the format: Bearer <token>.")

        token = header_parts[1].strip()
        try:
            payload = decode_access_token(token)
        except Exception as exc:
            raise AuthenticationFailed("Invalid or expired access token.") from exc

        user = self.user_repository.find_by_id(payload.get("sub"))
        if not user:
            raise AuthenticationFailed("User account was not found.")
        if user.get("role") != ROLE_SUPER_ADMIN and user.get("verification_status") != VERIFICATION_APPROVED:
            raise AuthenticationFailed("This account is not active.")

        return AuthenticatedUser.from_document(user), None
