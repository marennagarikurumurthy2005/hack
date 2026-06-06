from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from ..constants import FEEDBACK_STATUS_OPEN, ROLE_ADMIN
from ..permissions import has_role
from ..repositories import FeedbackRepository
from ..responses import api_response, paginated_response
from ..serializers import (
    CitizenFeedbackCreateSerializer,
    CitizenFeedbackRespondSerializer,
    CitizenFeedbackUpdateSerializer,
)
from ..services.auth_service import build_actor_snapshot
from ..services.media_service import upload_image
from ..utils import generate_reference, parse_bool, parse_pagination_params, serialize_value, utc_now


def can_view_feedback(user, feedback: dict) -> bool:
    if feedback.get("is_public"):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if has_role(user, {ROLE_ADMIN}):
        return True
    created_by = feedback.get("created_by") or {}
    return created_by.get("id") == getattr(user, "id", None)


def can_edit_feedback(user, feedback: dict) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if has_role(user, {ROLE_ADMIN}):
        return True
    created_by = feedback.get("created_by") or {}
    return created_by.get("id") == getattr(user, "id", None) and feedback.get("status") == FEEDBACK_STATUS_OPEN


class CitizenFeedbackListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.feedback_repository = FeedbackRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        filters = {
            "feedback_type": request.query_params.get("feedback_type"),
            "status": request.query_params.get("status"),
            "village": request.query_params.get("village"),
            "district": request.query_params.get("district"),
            "state": request.query_params.get("state"),
            "search": request.query_params.get("search"),
        }

        if parse_bool(request.query_params.get("mine")) and request.user:
            filters["created_by"] = request.user.id
        elif not has_role(request.user, {ROLE_ADMIN}):
            filters["public_only"] = True

        feedback_items, total = self.feedback_repository.list_feedback(filters, page, page_size)
        return paginated_response(
            [serialize_value(item) for item in feedback_items],
            page,
            page_size,
            total,
            message="Citizen feedback fetched successfully.",
        )

    def post(self, request):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            raise PermissionDenied("Authentication is required to submit citizen feedback.")

        serializer = CitizenFeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        images = [upload_image(file_obj, "feedback", field_name="images") for file_obj in request.FILES.getlist("images")]

        feedback = self.feedback_repository.create(
            {
                "feedback_number": generate_reference("FDB"),
                "feedback_type": validated_data["feedback_type"],
                "subject": validated_data["subject"],
                "message": validated_data["message"],
                "category": validated_data.get("category"),
                "status": FEEDBACK_STATUS_OPEN,
                "location": {
                    "village": validated_data["village"],
                    "ward_number": validated_data.get("ward_number"),
                    "district": validated_data["district"],
                    "state": validated_data["state"],
                },
                "is_public": validated_data.get("is_public", True),
                "images": images,
                "created_by": build_actor_snapshot(request.user),
                "response_message": None,
                "responded_by": None,
                "responded_at": None,
            }
        )
        return api_response(
            data={"feedback": serialize_value(feedback)},
            message="Citizen feedback submitted successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class CitizenFeedbackDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.feedback_repository = FeedbackRepository()

    def get(self, request, feedback_id: str):
        feedback = self.feedback_repository.find_by_id(feedback_id)
        if not feedback:
            raise NotFound("Citizen feedback was not found.")
        if not can_view_feedback(request.user, feedback):
            raise PermissionDenied("You do not have permission to view this feedback.")
        return api_response(
            data={"feedback": serialize_value(feedback)},
            message="Citizen feedback fetched successfully.",
        )

    def patch(self, request, feedback_id: str):
        feedback = self.feedback_repository.find_by_id(feedback_id)
        if not feedback:
            raise NotFound("Citizen feedback was not found.")
        if not can_edit_feedback(request.user, feedback):
            raise PermissionDenied("You do not have permission to update this feedback.")

        serializer = CitizenFeedbackUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updates = dict(serializer.validated_data)
        if request.FILES.getlist("images"):
            updates["images"] = [upload_image(file_obj, "feedback", field_name="images") for file_obj in request.FILES.getlist("images")]
        updated_feedback = self.feedback_repository.update_by_id(feedback["_id"], updates)
        return api_response(
            data={"feedback": serialize_value(updated_feedback)},
            message="Citizen feedback updated successfully.",
        )


class CitizenFeedbackRespondView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.feedback_repository = FeedbackRepository()

    def post(self, request, feedback_id: str):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can respond to citizen feedback.")

        feedback = self.feedback_repository.find_by_id(feedback_id)
        if not feedback:
            raise NotFound("Citizen feedback was not found.")

        serializer = CitizenFeedbackRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_feedback = self.feedback_repository.update_by_id(
            feedback["_id"],
            {
                "response_message": serializer.validated_data["response_message"],
                "status": serializer.validated_data["status"],
                "responded_by": build_actor_snapshot(request.user),
                "responded_at": utc_now(),
            },
        )
        return api_response(
            data={"feedback": serialize_value(updated_feedback)},
            message="Citizen feedback response saved successfully.",
        )
