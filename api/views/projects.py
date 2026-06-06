from datetime import date

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from ..constants import (
    ACTIVITY_STATUS_COMPLETED,
    MILESTONE_STATUS_ACHIEVED,
    ROLE_ADMIN,
    ROLE_GOVERNMENT_EMPLOYEE,
    ROLE_SUPER_ADMIN,
    ROLE_WARD_MEMBER,
    VERIFICATION_APPROVED,
)
from ..permissions import has_role
from ..repositories import ProjectRepository, UserRepository
from ..responses import api_response, paginated_response
from ..serializers import (
    ProjectActivityCreateSerializer,
    ProjectActivityUpdateSerializer,
    ProjectBudgetUpdateSerializer,
    ProjectCreateSerializer,
    ProjectExpenditureCreateSerializer,
    ProjectMilestoneCreateSerializer,
    ProjectMilestoneUpdateSerializer,
    ProjectProgressCreateSerializer,
    ProjectUpdateSerializer,
)
from ..services.auth_service import build_actor_snapshot
from ..utils import generate_reference, parse_bool, parse_pagination_params, serialize_value, utc_now


def normalize_date_fields(payload: dict, field_names: tuple[str, ...]):
    normalized = dict(payload)
    for field_name in field_names:
        if isinstance(normalized.get(field_name), date):
            normalized[field_name] = normalized[field_name].isoformat()
    return normalized


def unique_strings(values):
    output = []
    seen = set()
    for value in values or []:
        cleaned_value = str(value).strip()
        if cleaned_value and cleaned_value.lower() not in seen:
            output.append(cleaned_value)
            seen.add(cleaned_value.lower())
    return output


def resolve_internal_user(user_repository: UserRepository, user_id: str):
    user = user_repository.find_by_id(user_id)
    if not user:
        raise NotFound("Referenced user was not found.")
    if user.get("verification_status") != VERIFICATION_APPROVED:
        raise PermissionDenied("Referenced user must be approved.")
    if user.get("role") not in {ROLE_GOVERNMENT_EMPLOYEE, ROLE_WARD_MEMBER, ROLE_ADMIN, ROLE_SUPER_ADMIN}:
        raise PermissionDenied("Only operational users can own or manage projects.")
    return user


def resolve_user_snapshots(user_repository: UserRepository, user_ids):
    snapshots = []
    seen = set()
    for user_id in user_ids or []:
        if user_id in seen:
            continue
        snapshots.append(build_actor_snapshot(resolve_internal_user(user_repository, user_id)))
        seen.add(user_id)
    return snapshots


def is_project_team_member(user, project: dict) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "role", None) == ROLE_SUPER_ADMIN:
        return True
    owner = project.get("owner") or {}
    if owner.get("id") == getattr(user, "id", None):
        return True
    responsible_users = project.get("responsible_users") or []
    return any(item.get("id") == getattr(user, "id", None) for item in responsible_users)


def ensure_project_management_access(user, project: dict):
    if has_role(user, {ROLE_ADMIN}) or is_project_team_member(user, project):
        return
    raise PermissionDenied("You do not have permission to manage this project.")


def build_project_summary(project_repository: ProjectRepository, project: dict):
    project_id = project["_id"]
    activities_total = project_repository.activity_collection.count_documents({"project_id": project_id})
    activities_completed = project_repository.activity_collection.count_documents(
        {"project_id": project_id, "status": ACTIVITY_STATUS_COMPLETED}
    )
    milestones_total = project_repository.milestone_collection.count_documents({"project_id": project_id})
    milestones_achieved = project_repository.milestone_collection.count_documents(
        {"project_id": project_id, "status": MILESTONE_STATUS_ACHIEVED}
    )
    expenditures_total = project_repository.expenditure_collection.count_documents({"project_id": project_id})
    budget = project.get("budget", {})
    return {
        "activities_total": activities_total,
        "activities_completed": activities_completed,
        "milestones_total": milestones_total,
        "milestones_achieved": milestones_achieved,
        "progress_updates_total": project_repository.progress_collection.count_documents({"project_id": project_id}),
        "expenditures_total": expenditures_total,
        "budget": serialize_value(budget),
        "progress_percent": project.get("progress_percent", 0),
    }


def serialize_project_overview(project_repository: ProjectRepository, project: dict):
    serialized = serialize_value(project)
    serialized["summary_metrics"] = build_project_summary(project_repository, project)
    return serialized


def serialize_project_detail(project_repository: ProjectRepository, project: dict):
    serialized = serialize_project_overview(project_repository, project)
    serialized["activities"] = [serialize_value(item) for item in project_repository.list_activities(project["_id"])]
    serialized["milestones"] = [serialize_value(item) for item in project_repository.list_milestones(project["_id"])]
    serialized["progress_updates"] = [serialize_value(item) for item in project_repository.list_progress_updates(project["_id"])]
    serialized["expenditures"] = [serialize_value(item) for item in project_repository.list_expenditures(project["_id"])]
    return serialized


class ProjectListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()

    def get(self, request):
        page, page_size = parse_pagination_params(request.query_params)
        filters = {
            "status": request.query_params.get("status"),
            "workflow_stage": request.query_params.get("workflow_stage"),
            "priority": request.query_params.get("priority"),
            "village": request.query_params.get("village"),
            "district": request.query_params.get("district"),
            "state": request.query_params.get("state"),
            "owner_user_id": request.query_params.get("owner_user_id"),
            "responsible_user_id": request.query_params.get("responsible_user_id"),
            "search": request.query_params.get("search"),
        }
        if parse_bool(request.query_params.get("mine")) and request.user:
            filters["responsible_user_id"] = request.user.id
        projects, total = self.project_repository.list_projects(filters, page, page_size)
        return paginated_response(
            [serialize_project_overview(self.project_repository, project) for project in projects],
            page,
            page_size,
            total,
            message="Projects fetched successfully.",
        )

    def post(self, request):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can create development projects.")

        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(
            serializer.validated_data,
            ("start_date", "target_end_date", "end_date"),
        )

        owner = resolve_internal_user(self.user_repository, validated_data["owner_user_id"])
        responsible_users = resolve_user_snapshots(
            self.user_repository,
            unique_strings(validated_data.get("responsible_user_ids", [])),
        )
        villages = unique_strings(validated_data["villages"])
        allocated_amount = float(validated_data.get("budget_allocated_amount", 0) or 0)

        project = self.project_repository.create(
            {
                "project_number": generate_reference("PRJ"),
                "name": validated_data["name"],
                "summary": validated_data.get("summary"),
                "description": validated_data["description"],
                "category": validated_data["category"],
                "priority": validated_data["priority"],
                "status": validated_data["status"],
                "workflow_stage": validated_data["workflow_stage"],
                "villages": villages,
                "district": validated_data["district"],
                "state": validated_data["state"],
                "start_date": validated_data.get("start_date"),
                "target_end_date": validated_data.get("target_end_date"),
                "end_date": validated_data.get("end_date"),
                "owner": build_actor_snapshot(owner),
                "responsible_users": responsible_users,
                "budget": {
                    "allocated_amount": allocated_amount,
                    "spent_amount": 0.0,
                    "remaining_amount": allocated_amount,
                    "currency": validated_data.get("budget_currency", "INR"),
                    "allocations": validated_data.get("budget_allocations", []),
                },
                "tags": unique_strings(validated_data.get("tags", [])),
                "target_beneficiaries": validated_data.get("target_beneficiaries"),
                "progress_percent": 0,
                "created_by": build_actor_snapshot(request.user),
                "updated_by": build_actor_snapshot(request.user),
            }
        )

        return api_response(
            data={"project": serialize_project_detail(self.project_repository, project)},
            message="Project created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ProjectDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()

    def get(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        return api_response(
            data={"project": serialize_project_detail(self.project_repository, project)},
            message="Project fetched successfully.",
        )

    def patch(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(
            serializer.validated_data,
            ("start_date", "target_end_date", "end_date"),
        )
        updates = {}

        for field_name in (
            "name",
            "summary",
            "description",
            "category",
            "priority",
            "status",
            "workflow_stage",
            "villages",
            "district",
            "state",
            "start_date",
            "target_end_date",
            "end_date",
            "target_beneficiaries",
            "tags",
        ):
            if field_name in validated_data:
                updates[field_name] = (
                    unique_strings(validated_data[field_name])
                    if field_name in {"villages", "tags"}
                    else validated_data[field_name]
                )

        if "owner_user_id" in validated_data:
            updates["owner"] = build_actor_snapshot(
                resolve_internal_user(self.user_repository, validated_data["owner_user_id"])
            )
        if "responsible_user_ids" in validated_data:
            updates["responsible_users"] = resolve_user_snapshots(
                self.user_repository,
                unique_strings(validated_data["responsible_user_ids"]),
            )
        if {"budget_allocated_amount", "budget_currency", "budget_allocations"} & set(validated_data.keys()):
            existing_budget = project.get("budget", {})
            allocated_amount = float(
                validated_data.get("budget_allocated_amount", existing_budget.get("allocated_amount", 0)) or 0
            )
            spent_amount = float(existing_budget.get("spent_amount", 0) or 0)
            updates["budget"] = {
                "allocated_amount": allocated_amount,
                "spent_amount": spent_amount,
                "remaining_amount": round(allocated_amount - spent_amount, 2),
                "currency": validated_data.get("budget_currency", existing_budget.get("currency", "INR")),
                "allocations": validated_data.get("budget_allocations", existing_budget.get("allocations", [])),
            }

        updates["updated_by"] = build_actor_snapshot(request.user)
        updated_project = self.project_repository.update_by_id(project["_id"], updates)
        return api_response(
            data={"project": serialize_project_detail(self.project_repository, updated_project)},
            message="Project updated successfully.",
        )

    def delete(self, request, project_id: str):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can delete projects.")
        deleted = self.project_repository.delete_by_id(project_id)
        if not deleted:
            raise NotFound("Project was not found.")
        return api_response(message="Project deleted successfully.")


class ProjectActivityListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()

    def get(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        return api_response(
            data={"activities": [serialize_value(item) for item in self.project_repository.list_activities(project["_id"])]},
            message="Project activities fetched successfully.",
        )

    def post(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        serializer = ProjectActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(serializer.validated_data, ("due_date", "start_date", "end_date"))
        assigned_to = None
        if validated_data.get("assigned_to_user_id"):
            assigned_to = build_actor_snapshot(
                resolve_internal_user(self.user_repository, validated_data["assigned_to_user_id"])
            )

        activity = self.project_repository.create_activity(
            {
                "project_id": project["_id"],
                "title": validated_data["title"],
                "description": validated_data.get("description"),
                "status": validated_data["status"],
                "assigned_to": assigned_to,
                "due_date": validated_data.get("due_date"),
                "start_date": validated_data.get("start_date"),
                "end_date": validated_data.get("end_date"),
                "priority": validated_data["priority"],
                "dependency_ids": unique_strings(validated_data.get("dependency_ids", [])),
                "created_by": build_actor_snapshot(request.user),
            }
        )
        return api_response(
            data={"activity": serialize_value(activity)},
            message="Project activity created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ProjectActivityDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()

    def patch(self, request, project_id: str, activity_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        activity = self.project_repository.find_activity_by_id(project["_id"], activity_id)
        if not activity:
            raise NotFound("Project activity was not found.")

        serializer = ProjectActivityUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(serializer.validated_data, ("due_date", "start_date", "end_date"))
        updates = {}
        for field_name in ("title", "description", "status", "due_date", "start_date", "end_date", "priority"):
            if field_name in validated_data:
                updates[field_name] = validated_data[field_name]
        if "dependency_ids" in validated_data:
            updates["dependency_ids"] = unique_strings(validated_data["dependency_ids"])
        if "assigned_to_user_id" in validated_data:
            updates["assigned_to"] = (
                build_actor_snapshot(resolve_internal_user(self.user_repository, validated_data["assigned_to_user_id"]))
                if validated_data["assigned_to_user_id"]
                else None
            )
        if updates.get("status") == ACTIVITY_STATUS_COMPLETED and not updates.get("end_date"):
            updates["end_date"] = utc_now().date().isoformat()
        updated_activity = self.project_repository.update_activity(project["_id"], activity["_id"], updates)
        return api_response(
            data={"activity": serialize_value(updated_activity)},
            message="Project activity updated successfully.",
        )


class ProjectMilestoneListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()

    def get(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        return api_response(
            data={"milestones": [serialize_value(item) for item in self.project_repository.list_milestones(project["_id"])]},
            message="Project milestones fetched successfully.",
        )

    def post(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        serializer = ProjectMilestoneCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(serializer.validated_data, ("target_date",))
        milestone = self.project_repository.create_milestone(
            {
                "project_id": project["_id"],
                "title": validated_data["title"],
                "description": validated_data.get("description"),
                "target_date": validated_data.get("target_date"),
                "status": validated_data["status"],
                "weight_percent": validated_data.get("weight_percent", 0),
                "created_by": build_actor_snapshot(request.user),
            }
        )
        return api_response(
            data={"milestone": serialize_value(milestone)},
            message="Project milestone created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ProjectMilestoneDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()

    def patch(self, request, project_id: str, milestone_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        milestone = self.project_repository.find_milestone_by_id(project["_id"], milestone_id)
        if not milestone:
            raise NotFound("Project milestone was not found.")

        serializer = ProjectMilestoneUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(serializer.validated_data, ("target_date",))
        updates = dict(validated_data)
        if updates.get("status") == MILESTONE_STATUS_ACHIEVED:
            updates["achieved_at"] = utc_now().date().isoformat()
        updated_milestone = self.project_repository.update_milestone(project["_id"], milestone["_id"], updates)
        return api_response(
            data={"milestone": serialize_value(updated_milestone)},
            message="Project milestone updated successfully.",
        )


class ProjectProgressListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()

    def get(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        return api_response(
            data={"progress_updates": [serialize_value(item) for item in self.project_repository.list_progress_updates(project["_id"])]},
            message="Project progress updates fetched successfully.",
        )

    def post(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        serializer = ProjectProgressCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        progress_update = self.project_repository.create_progress_update(
            {
                "project_id": project["_id"],
                "message": validated_data["message"],
                "progress_percent": validated_data.get("progress_percent", project.get("progress_percent", 0)),
                "status": validated_data.get("status", project.get("status")),
                "workflow_stage": validated_data.get("workflow_stage", project.get("workflow_stage")),
                "risk_level": validated_data.get("risk_level"),
                "created_by": build_actor_snapshot(request.user),
            }
        )

        updates = {
            "latest_update": {
                "message": validated_data["message"],
                "created_at": progress_update["created_at"],
                "created_by": build_actor_snapshot(request.user),
            },
            "updated_by": build_actor_snapshot(request.user),
        }
        if "progress_percent" in validated_data:
            updates["progress_percent"] = validated_data["progress_percent"]
        if "status" in validated_data:
            updates["status"] = validated_data["status"]
        if "workflow_stage" in validated_data:
            updates["workflow_stage"] = validated_data["workflow_stage"]
        updated_project = self.project_repository.update_by_id(project["_id"], updates)
        return api_response(
            data={
                "progress_update": serialize_value(progress_update),
                "project": serialize_project_detail(self.project_repository, updated_project),
            },
            message="Project progress update created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ProjectExpenditureListCreateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()
        self.user_repository = UserRepository()

    def get(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        return api_response(
            data={"expenditures": [serialize_value(item) for item in self.project_repository.list_expenditures(project["_id"])]},
            message="Project expenditures fetched successfully.",
        )

    def post(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        ensure_project_management_access(request.user, project)

        serializer = ProjectExpenditureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = normalize_date_fields(serializer.validated_data, ("spent_on",))
        approved_by = None
        if validated_data.get("approved_by_user_id"):
            approved_by = build_actor_snapshot(
                resolve_internal_user(self.user_repository, validated_data["approved_by_user_id"])
            )
        expenditure = self.project_repository.create_expenditure(
            {
                "project_id": project["_id"],
                "amount": float(validated_data["amount"]),
                "category": validated_data["category"],
                "description": validated_data["description"],
                "spent_on": validated_data.get("spent_on") or utc_now().date().isoformat(),
                "vendor": validated_data.get("vendor"),
                "receipt_reference": validated_data.get("receipt_reference"),
                "approved_by": approved_by,
                "created_by": build_actor_snapshot(request.user),
            }
        )
        updated_project = self.project_repository.recalculate_budget(project["_id"])
        return api_response(
            data={
                "expenditure": serialize_value(expenditure),
                "budget": serialize_value(updated_project.get("budget", {})) if updated_project else {},
            },
            message="Project expenditure recorded successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ProjectBudgetUpdateView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.project_repository = ProjectRepository()

    def patch(self, request, project_id: str):
        project = self.project_repository.find_by_id(project_id)
        if not project:
            raise NotFound("Project was not found.")
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can manage project budgets.")

        serializer = ProjectBudgetUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        existing_budget = project.get("budget", {})
        allocated_amount = float(validated_data["allocated_amount"])
        spent_amount = float(existing_budget.get("spent_amount", 0) or 0)
        updated_project = self.project_repository.update_by_id(
            project["_id"],
            {
                "budget": {
                    "allocated_amount": allocated_amount,
                    "spent_amount": spent_amount,
                    "remaining_amount": round(allocated_amount - spent_amount, 2),
                    "currency": validated_data.get("currency", existing_budget.get("currency", "INR")),
                    "allocations": validated_data.get("allocations", existing_budget.get("allocations", [])),
                    "notes": validated_data.get("notes"),
                },
                "updated_by": build_actor_snapshot(request.user),
            },
        )
        return api_response(
            data={"budget": serialize_value(updated_project.get("budget", {}))},
            message="Project budget updated successfully.",
        )
