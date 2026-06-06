from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from ..constants import (
    COMPLAINT_STATUS_ASSIGNED,
    COMPLAINT_STATUS_IN_PROGRESS,
    COMPLAINT_STATUS_OPEN,
    COMPLAINT_STATUS_RESOLVED,
    ROLE_ADMIN,
    ROLE_GOVERNMENT_EMPLOYEE,
    ROLE_WARD_MEMBER,
    VERIFICATION_APPROVED,
)
from ..permissions import IsAdminOrSuperAdmin, IsAuthenticatedUser, has_role
from ..repositories import ComplaintRepository, UserRepository
from ..responses import api_response, paginated_response
from ..serializers import (
    ComplaintAssignSerializer,
    ComplaintCreateSerializer,
    ComplaintProgressSerializer,
    ComplaintUpdateSerializer,
)
from ..services.auth_service import build_actor_snapshot, serialize_user_for_public
from ..services.media_service import upload_image
from ..utils import generate_reference, parse_bool, parse_pagination_params, serialize_value, utc_now


class ComplaintListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.complaint_repository = ComplaintRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        filters = {
            "status": request.query_params.get("status"),
            "priority": request.query_params.get("priority"),
            "category": request.query_params.get("category"),
            "village": request.query_params.get("village"),
            "district": request.query_params.get("district"),
            "state": request.query_params.get("state"),
            "ward_number": request.query_params.get("ward_number"),
            "complaint_number": request.query_params.get("complaint_number"),
            "created_by": request.query_params.get("created_by"),
            "assigned_to": request.query_params.get("assigned_to"),
            "search": request.query_params.get("search"),
        }

        if parse_bool(request.query_params.get("mine")) and request.user:
            filters["created_by"] = request.user.id

        complaints, total = self.complaint_repository.list_complaints(filters, page, page_size)
        serialized = [serialize_value(item) for item in complaints]
        return paginated_response(serialized, page, page_size, total, message="Complaints fetched successfully.")

    def post(self, request):
        if not has_role(request.user, {"citizen"}):
            raise PermissionDenied("Only approved citizens or super admins can create complaints.")

        serializer = ComplaintCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        images = [upload_image(file_obj, "complaints", field_name="images") for file_obj in request.FILES.getlist("images")]
        complaint = self.complaint_repository.create(
            {
                "complaint_number": generate_reference("CMP"),
                "title": validated_data["title"],
                "category": validated_data["category"],
                "description": validated_data["description"],
                "priority": validated_data["priority"],
                "status": COMPLAINT_STATUS_OPEN,
                "location": {
                    "village": validated_data["village"],
                    "ward_number": validated_data.get("ward_number"),
                    "district": validated_data["district"],
                    "state": validated_data["state"],
                    "pincode": validated_data["pincode"],
                    "address_line1": validated_data["address_line1"],
                    "address_line2": validated_data.get("address_line2"),
                    "landmark": validated_data.get("landmark"),
                    "latitude": float(validated_data["latitude"]) if validated_data.get("latitude") is not None else None,
                    "longitude": float(validated_data["longitude"]) if validated_data.get("longitude") is not None else None,
                },
                "images": images,
                "created_by": build_actor_snapshot(request.user),
                "assigned_to": None,
                "progress_percent": 0,
                "resolution_summary": None,
            }
        )
        self.complaint_repository.create_progress(
            {
                "complaint_id": complaint["_id"],
                "message": "Complaint submitted successfully.",
                "status": COMPLAINT_STATUS_OPEN,
                "progress_percent": 0,
                "visibility": "public",
                "images": images,
                "created_by": build_actor_snapshot(request.user),
            }
        )
        return api_response(
            data={"complaint": serialize_value(complaint)},
            message="Complaint created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ComplaintDetailUpdateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.complaint_repository = ComplaintRepository()

    def _can_view_internal_progress(self, request, complaint):
        if has_role(request.user, {ROLE_ADMIN}):
            return True
        assigned_to = complaint.get("assigned_to") or {}
        return bool(request.user and assigned_to.get("id") == request.user.id)

    def get(self, request, complaint_id: str):
        complaint = self.complaint_repository.find_by_id(complaint_id)
        if not complaint:
            raise NotFound("Complaint was not found.")

        include_internal_progress = self._can_view_internal_progress(request, complaint)
        serialized_complaint = serialize_value(complaint)
        serialized_complaint["progress_updates"] = [
            serialize_value(item)
            for item in self.complaint_repository.list_progress(complaint["_id"], include_internal=include_internal_progress)
        ]
        return api_response(
            data={"complaint": serialized_complaint},
            message="Complaint fetched successfully.",
        )

    def patch(self, request, complaint_id: str):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can update complaint details.")

        complaint = self.complaint_repository.find_by_id(complaint_id)
        if not complaint:
            raise NotFound("Complaint was not found.")

        serializer = ComplaintUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updates = {}
        location_updates = {}

        for field in ("title", "category", "description", "priority", "status", "resolution_summary"):
            if field in serializer.validated_data:
                updates[field] = serializer.validated_data[field]

        for field in ("village", "ward_number", "district", "state", "pincode", "address_line1", "address_line2", "landmark"):
            if field in serializer.validated_data:
                location_updates[field] = serializer.validated_data[field]

        if "latitude" in serializer.validated_data:
            location_updates["latitude"] = (
                float(serializer.validated_data["latitude"]) if serializer.validated_data["latitude"] is not None else None
            )
        if "longitude" in serializer.validated_data:
            location_updates["longitude"] = (
                float(serializer.validated_data["longitude"]) if serializer.validated_data["longitude"] is not None else None
            )

        if location_updates:
            existing_location = complaint.get("location", {})
            updates["location"] = {**existing_location, **location_updates}

        updated_complaint = self.complaint_repository.update_by_id(complaint["_id"], updates)
        return api_response(
            data={"complaint": serialize_value(updated_complaint)},
            message="Complaint updated successfully.",
        )


class ComplaintAssignView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.complaint_repository = ComplaintRepository()
        self.user_repository = UserRepository()

    def patch(self, request, complaint_id: str):
        complaint = self.complaint_repository.find_by_id(complaint_id)
        if not complaint:
            raise NotFound("Complaint was not found.")

        serializer = ComplaintAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignee = self.user_repository.find_by_id(serializer.validated_data["assigned_to"])
        if not assignee:
            raise NotFound("Assignee user was not found.")
        if assignee.get("role") not in {ROLE_GOVERNMENT_EMPLOYEE, ROLE_WARD_MEMBER, ROLE_ADMIN}:
            raise PermissionDenied("Complaints can only be assigned to government employees, ward members, or admins.")
        if assignee.get("verification_status") != VERIFICATION_APPROVED:
            raise PermissionDenied("Only approved operational users can be assigned complaints.")

        updated_complaint = self.complaint_repository.update_by_id(
            complaint["_id"],
            {
                "assigned_to": build_actor_snapshot(assignee),
                "assigned_at": utc_now(),
                "status": COMPLAINT_STATUS_ASSIGNED,
            },
        )
        assignment_note = serializer.validated_data.get("assignment_note") or f"Complaint assigned to {assignee.get('full_name')}."
        self.complaint_repository.create_progress(
            {
                "complaint_id": complaint["_id"],
                "message": assignment_note,
                "status": COMPLAINT_STATUS_ASSIGNED,
                "progress_percent": updated_complaint.get("progress_percent", 0),
                "visibility": "public",
                "images": [],
                "created_by": build_actor_snapshot(request.user),
            }
        )
        return api_response(
            data={"complaint": serialize_value(updated_complaint)},
            message="Complaint assigned successfully.",
        )


class ComplaintProgressListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.complaint_repository = ComplaintRepository()

    def _can_manage_progress(self, request, complaint):
        if has_role(request.user, {ROLE_ADMIN}):
            return True
        assigned_to = complaint.get("assigned_to") or {}
        return bool(request.user and assigned_to.get("id") == request.user.id)

    def get(self, request, complaint_id: str):
        complaint = self.complaint_repository.find_by_id(complaint_id)
        if not complaint:
            raise NotFound("Complaint was not found.")

        include_internal = self._can_manage_progress(request, complaint)
        progress_updates = self.complaint_repository.list_progress(complaint["_id"], include_internal=include_internal)
        return api_response(
            data={"progress_updates": [serialize_value(item) for item in progress_updates]},
            message="Complaint progress fetched successfully.",
        )

    def post(self, request, complaint_id: str):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            raise PermissionDenied("Authentication is required to add progress updates.")

        complaint = self.complaint_repository.find_by_id(complaint_id)
        if not complaint:
            raise NotFound("Complaint was not found.")
        if not self._can_manage_progress(request, complaint):
            raise PermissionDenied("Only the assigned operational user, admin, or super admin can add progress updates.")

        serializer = ComplaintProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        images = [upload_image(file_obj, "progress", field_name="images") for file_obj in request.FILES.getlist("images")]

        progress_update = self.complaint_repository.create_progress(
            {
                "complaint_id": complaint["_id"],
                "message": validated_data["message"],
                "status": validated_data.get("status", complaint.get("status")),
                "progress_percent": validated_data.get("progress_percent", complaint.get("progress_percent", 0)),
                "visibility": validated_data.get("visibility", "public"),
                "images": images,
                "created_by": build_actor_snapshot(request.user),
            }
        )

        complaint_updates = {
            "latest_progress": {
                "message": validated_data["message"],
                "created_at": progress_update["created_at"],
                "created_by": build_actor_snapshot(request.user),
            }
        }
        if "status" in validated_data:
            complaint_updates["status"] = validated_data["status"]
        if "progress_percent" in validated_data:
            complaint_updates["progress_percent"] = validated_data["progress_percent"]
        if validated_data.get("status") == COMPLAINT_STATUS_RESOLVED and "progress_percent" not in validated_data:
            complaint_updates["progress_percent"] = 100
        if validated_data.get("status") == COMPLAINT_STATUS_IN_PROGRESS and complaint.get("status") == COMPLAINT_STATUS_OPEN:
            complaint_updates["status"] = COMPLAINT_STATUS_IN_PROGRESS

        updated_complaint = self.complaint_repository.update_by_id(complaint["_id"], complaint_updates)
        return api_response(
            data={
                "progress_update": serialize_value(progress_update),
                "complaint": serialize_value(updated_complaint),
            },
            message="Complaint progress added successfully.",
            status_code=status.HTTP_201_CREATED,
        )
