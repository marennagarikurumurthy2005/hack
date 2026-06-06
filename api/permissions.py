from rest_framework.permissions import BasePermission

from .constants import ROLE_ADMIN, ROLE_CITIZEN, ROLE_GOVERNMENT_EMPLOYEE, ROLE_SUPER_ADMIN, ROLE_WARD_MEMBER


def has_role(user, allowed_roles) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role", None)
    return role == ROLE_SUPER_ADMIN or role in allowed_roles


class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and getattr(request.user, "is_authenticated", False))


class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return has_role(request.user, {ROLE_ADMIN})


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return has_role(request.user, {ROLE_SUPER_ADMIN})


class IsCitizenOrSuperAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return has_role(request.user, {ROLE_CITIZEN})


class IsOperationsUser(BasePermission):
    def has_permission(self, request, view) -> bool:
        return has_role(request.user, {ROLE_GOVERNMENT_EMPLOYEE, ROLE_WARD_MEMBER, ROLE_ADMIN})
