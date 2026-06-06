from datetime import date

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from ..constants import ROLE_ADMIN, SCHEME_STATUS_PUBLISHED
from ..permissions import IsAdminOrSuperAdmin, has_role
from ..repositories import SchemeRepository
from ..responses import api_response, paginated_response
from ..serializers import SchemeSerializer
from ..services.auth_service import build_actor_snapshot
from ..services.media_service import upload_image
from ..utils import parse_pagination_params, serialize_value


def normalize_scheme_payload(payload: dict) -> dict:
    normalized = dict(payload)
    for field in ("start_date", "end_date"):
        if isinstance(normalized.get(field), date):
            normalized[field] = normalized[field].isoformat()
    return normalized


class SchemeListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scheme_repository = SchemeRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        filters = {
            "status": request.query_params.get("status"),
            "department": request.query_params.get("department"),
            "village": request.query_params.get("village"),
            "search": request.query_params.get("search"),
        }
        if not has_role(request.user, {ROLE_ADMIN}):
            filters["status"] = SCHEME_STATUS_PUBLISHED

        schemes, total = self.scheme_repository.list_schemes(filters, page, page_size)
        return paginated_response(
            [serialize_value(scheme) for scheme in schemes],
            page,
            page_size,
            total,
            message="Schemes fetched successfully.",
        )

    def post(self, request):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can create schemes.")

        serializer = SchemeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_scheme_payload(serializer.validated_data)
        banner_image = validated_data.pop("banner_image", None)
        if banner_image:
            validated_data["banner_image"] = upload_image(
                banner_image,
                "schemes",
                field_name="banner_image",
            )

        scheme = self.scheme_repository.create(
            {
                **validated_data,
                "created_by": build_actor_snapshot(request.user),
                "updated_by": build_actor_snapshot(request.user),
            }
        )
        return api_response(
            data={"scheme": serialize_value(scheme)},
            message="Scheme created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class SchemeDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scheme_repository = SchemeRepository()

    def get(self, request, scheme_id: str):
        scheme = self.scheme_repository.find_by_id(scheme_id)
        if not scheme:
            raise NotFound("Scheme was not found.")
        if scheme.get("status") != SCHEME_STATUS_PUBLISHED and not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("This scheme is not publicly available.")
        return api_response(data={"scheme": serialize_value(scheme)}, message="Scheme fetched successfully.")

    def patch(self, request, scheme_id: str):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can update schemes.")

        scheme = self.scheme_repository.find_by_id(scheme_id)
        if not scheme:
            raise NotFound("Scheme was not found.")

        serializer = SchemeSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updates = normalize_scheme_payload(serializer.validated_data)
        banner_image = updates.pop("banner_image", None)
        if banner_image:
            updates["banner_image"] = upload_image(
                banner_image,
                "schemes",
                field_name="banner_image",
            )
        updates["updated_by"] = build_actor_snapshot(request.user)

        updated_scheme = self.scheme_repository.update_by_id(scheme["_id"], updates)
        return api_response(data={"scheme": serialize_value(updated_scheme)}, message="Scheme updated successfully.")

    def delete(self, request, scheme_id: str):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can delete schemes.")

        deleted = self.scheme_repository.delete_by_id(scheme_id)
        if not deleted:
            raise NotFound("Scheme was not found.")
        return api_response(message="Scheme deleted successfully.", status_code=status.HTTP_200_OK)
