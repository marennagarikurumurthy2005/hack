from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from ..constants import ROLE_SUPER_ADMIN, VERIFICATION_APPROVED
from ..permissions import IsAdminOrSuperAdmin, IsAuthenticatedUser, IsSuperAdmin, has_role
from ..repositories import UserRepository
from ..responses import api_response, paginated_response
from ..serializers import UserRoleUpdateSerializer, UserVerificationSerializer
from ..services.auth_service import build_actor_snapshot, serialize_user_for_response
from ..utils import parse_pagination_params, utc_now


class UserListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        filters = {
            "role": request.query_params.get("role"),
            "verification_status": request.query_params.get("verification_status"),
            "village": request.query_params.get("village"),
            "district": request.query_params.get("district"),
            "search": request.query_params.get("search"),
        }
        users, total = self.user_repository.list_users(filters, page, page_size)
        serialized = [serialize_user_for_response(user, include_confidential=True) for user in users]
        return paginated_response(serialized, page, page_size, total, message="Users fetched successfully.")


class PendingUserListView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        users, total = self.user_repository.list_users(
            {"verification_status": "pending", "role": request.query_params.get("role"), "search": request.query_params.get("search")},
            page,
            page_size,
        )
        serialized = [serialize_user_for_response(user, include_confidential=True) for user in users]
        return paginated_response(serialized, page, page_size, total, message="Pending users fetched successfully.")


class UserDetailView(APIView):
    permission_classes = [IsAuthenticatedUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def get(self, request, user_id: str):
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise NotFound("User was not found.")

        is_self = request.user.id == str(user["_id"])
        if not is_self and not has_role(request.user, {"admin"}):
            raise PermissionDenied("You do not have permission to access this user.")

        return api_response(
            data={"user": serialize_user_for_response(user, include_confidential=True)},
            message="User fetched successfully.",
        )


class UserVerificationView(APIView):
    permission_classes = [IsSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def patch(self, request, user_id: str):
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise NotFound("User was not found.")

        serializer = UserVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_user = self.user_repository.update_by_id(
            user["_id"],
            {
                "verification_status": serializer.validated_data["verification_status"],
                "review_notes": serializer.validated_data.get("review_notes"),
                "verified_at": utc_now(),
                "verified_by": build_actor_snapshot(request.user),
            },
        )
        return api_response(
            data={"user": serialize_user_for_response(updated_user, include_confidential=True)},
            message="User verification status updated successfully.",
        )


class UserRoleUpdateView(APIView):
    permission_classes = [IsSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()

    def patch(self, request, user_id: str):
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise NotFound("User was not found.")

        serializer = UserRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if user.get("role") == ROLE_SUPER_ADMIN and request.user.id == str(user["_id"]):
            raise PermissionDenied("Super admins cannot change their own role through this endpoint.")

        updates = {"role": serializer.validated_data["role"]}
        if serializer.validated_data["role"] == ROLE_SUPER_ADMIN:
            updates["verification_status"] = VERIFICATION_APPROVED
            updates["review_notes"] = "Auto-approved on promotion to super admin."
            updates["verified_at"] = utc_now()
            updates["verified_by"] = build_actor_snapshot(request.user)

        updated_user = self.user_repository.update_by_id(user["_id"], updates)
        return api_response(
            data={"user": serialize_user_for_response(updated_user, include_confidential=True)},
            message="User role updated successfully.",
        )
