import re

from pymongo import ASCENDING, DESCENDING

from .constants import (
    COMPLAINT_STATUSES,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    PROJECT_STATUSES,
    PROJECT_WORKFLOW_STAGES,
    ROLE_ADMIN,
    ROLE_CITIZEN,
    ROLE_GOVERNMENT_EMPLOYEE,
    ROLE_SUPER_ADMIN,
    ROLE_WARD_MEMBER,
    SCHEME_STATUSES,
    USER_ROLES,
    VERIFICATION_STATUSES,
)
from .mongodb import get_collection
from .utils import maybe_object_id, utc_now


class UserRepository:
    def __init__(self) -> None:
        self.collection = get_collection("users")

    def ensure_indexes(self) -> None:
        self.collection.create_index("email", unique=True, sparse=True)
        self.collection.create_index("username", unique=True, sparse=True)
        self.collection.create_index("mobile_number", unique=True)
        self.collection.create_index("government_id_number", unique=True, sparse=True)
        self.collection.create_index("employee_id", unique=True, sparse=True)
        self.collection.create_index([("role", ASCENDING), ("verification_status", ASCENDING)])
        self.collection.create_index([("village", ASCENDING), ("district", ASCENDING)])

    def create(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.collection.insert_one(payload)
        return self.find_by_id(result.inserted_id)

    def find_by_id(self, user_id):
        object_id = maybe_object_id(user_id)
        if object_id is None:
            return None
        return self.collection.find_one({"_id": object_id})

    def find_by_email(self, email: str):
        return self.collection.find_one({"email": email.strip().lower()})

    def find_by_username(self, username: str):
        return self.collection.find_one({"username": username.strip().lower()})

    def find_by_mobile_number(self, mobile_number: str):
        return self.collection.find_one({"mobile_number": mobile_number.strip()})

    def find_by_government_id_number(self, government_id_number: str):
        return self.collection.find_one({"government_id_number": government_id_number.strip()})

    def find_by_employee_id(self, employee_id: str):
        return self.collection.find_one({"employee_id": employee_id.strip()})

    def find_by_identifier(self, identifier: str):
        cleaned_identifier = identifier.strip()
        return self.collection.find_one(
            {
                "$or": [
                    {"email": cleaned_identifier.lower()},
                    {"username": cleaned_identifier.lower()},
                    {"mobile_number": cleaned_identifier},
                ]
            }
        )

    def update_by_id(self, user_id, updates: dict):
        object_id = maybe_object_id(user_id)
        if object_id is None:
            return None
        payload = {**updates, "updated_at": utc_now()}
        self.collection.update_one({"_id": object_id}, {"$set": payload})
        return self.find_by_id(object_id)

    def list_users(self, filters: dict, page: int, page_size: int):
        query = {}
        role = filters.get("role")
        verification_status = filters.get("verification_status")
        village = filters.get("village")
        district = filters.get("district")
        search = filters.get("search")

        if role:
            query["role"] = role
        if verification_status:
            query["verification_status"] = verification_status
        if village:
            query["village"] = {"$regex": f"^{re.escape(village)}$", "$options": "i"}
        if district:
            query["district"] = {"$regex": f"^{re.escape(district)}$", "$options": "i"}
        if search:
            query["$or"] = [
                {"full_name": {"$regex": re.escape(search), "$options": "i"}},
                {"email": {"$regex": re.escape(search), "$options": "i"}},
                {"username": {"$regex": re.escape(search), "$options": "i"}},
                {"mobile_number": {"$regex": re.escape(search), "$options": "i"}},
                {"government_id_number": {"$regex": re.escape(search), "$options": "i"}},
                {"employee_id": {"$regex": re.escape(search), "$options": "i"}},
            ]

        total = self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return list(cursor), total

    def count_by_role(self):
        return {role: self.collection.count_documents({"role": role}) for role in USER_ROLES}

    def count_by_verification_status(self):
        return {
            status: self.collection.count_documents({"verification_status": status})
            for status in VERIFICATION_STATUSES
        }


class ComplaintRepository:
    def __init__(self) -> None:
        self.collection = get_collection("complaints")
        self.progress_collection = get_collection("complaint_progress")

    def ensure_indexes(self) -> None:
        self.collection.create_index("complaint_number", unique=True)
        self.collection.create_index([("status", ASCENDING), ("priority", ASCENDING)])
        self.collection.create_index([("location.village", ASCENDING), ("location.district", ASCENDING)])
        self.collection.create_index([("created_by.id", ASCENDING), ("assigned_to.id", ASCENDING)])
        self.progress_collection.create_index([("complaint_id", ASCENDING), ("created_at", DESCENDING)])

    def create(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.collection.insert_one(payload)
        return self.find_by_id(result.inserted_id)

    def find_by_id(self, complaint_id):
        object_id = maybe_object_id(complaint_id)
        if object_id is None:
            return None
        return self.collection.find_one({"_id": object_id})

    def update_by_id(self, complaint_id, updates: dict):
        object_id = maybe_object_id(complaint_id)
        if object_id is None:
            return None
        payload = {**updates, "updated_at": utc_now()}
        self.collection.update_one({"_id": object_id}, {"$set": payload})
        return self.find_by_id(object_id)

    def list_complaints(self, filters: dict, page: int, page_size: int):
        query = {}
        status = filters.get("status")
        priority = filters.get("priority")
        category = filters.get("category")
        village = filters.get("village")
        district = filters.get("district")
        state = filters.get("state")
        ward_number = filters.get("ward_number")
        complaint_number = filters.get("complaint_number")
        created_by = filters.get("created_by")
        assigned_to = filters.get("assigned_to")
        search = filters.get("search")

        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        if category:
            query["category"] = {"$regex": f"^{re.escape(category)}$", "$options": "i"}
        if village:
            query["location.village"] = {"$regex": f"^{re.escape(village)}$", "$options": "i"}
        if district:
            query["location.district"] = {"$regex": f"^{re.escape(district)}$", "$options": "i"}
        if state:
            query["location.state"] = {"$regex": f"^{re.escape(state)}$", "$options": "i"}
        if ward_number:
            query["location.ward_number"] = {"$regex": f"^{re.escape(ward_number)}$", "$options": "i"}
        if complaint_number:
            query["complaint_number"] = complaint_number
        if created_by:
            query["created_by.id"] = str(created_by)
        if assigned_to:
            query["assigned_to.id"] = str(assigned_to)
        if search:
            query["$or"] = [
                {"title": {"$regex": re.escape(search), "$options": "i"}},
                {"description": {"$regex": re.escape(search), "$options": "i"}},
                {"complaint_number": {"$regex": re.escape(search), "$options": "i"}},
                {"location.address_line1": {"$regex": re.escape(search), "$options": "i"}},
            ]

        total = self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return list(cursor), total

    def create_progress(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.progress_collection.insert_one(payload)
        return self.progress_collection.find_one({"_id": result.inserted_id})

    def list_progress(self, complaint_id, include_internal: bool = False):
        object_id = maybe_object_id(complaint_id)
        if object_id is None:
            return []
        query = {"complaint_id": object_id}
        if not include_internal:
            query["visibility"] = "public"
        return list(self.progress_collection.find(query).sort("created_at", DESCENDING))

    def count_by_status(self):
        return {status: self.collection.count_documents({"status": status}) for status in COMPLAINT_STATUSES}

    def count_high_priority(self):
        return self.collection.count_documents({"priority": {"$in": ["high", "critical"]}})

    def count_for_village(self, village: str):
        return self.collection.count_documents(
            {"location.village": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}
        )

    def recent_for_village(self, village: str, limit: int = 5):
        return list(
            self.collection.find(
                {"location.village": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )


class SchemeRepository:
    def __init__(self) -> None:
        self.collection = get_collection("schemes")

    def ensure_indexes(self) -> None:
        self.collection.create_index([("status", ASCENDING), ("department", ASCENDING)])
        self.collection.create_index([("village_tags", ASCENDING)])

    def create(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.collection.insert_one(payload)
        return self.find_by_id(result.inserted_id)

    def find_by_id(self, scheme_id):
        object_id = maybe_object_id(scheme_id)
        if object_id is None:
            return None
        return self.collection.find_one({"_id": object_id})

    def update_by_id(self, scheme_id, updates: dict):
        object_id = maybe_object_id(scheme_id)
        if object_id is None:
            return None
        payload = {**updates, "updated_at": utc_now()}
        self.collection.update_one({"_id": object_id}, {"$set": payload})
        return self.find_by_id(object_id)

    def delete_by_id(self, scheme_id) -> bool:
        object_id = maybe_object_id(scheme_id)
        if object_id is None:
            return False
        result = self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    def list_schemes(self, filters: dict, page: int, page_size: int):
        query = {}
        status = filters.get("status")
        department = filters.get("department")
        village = filters.get("village")
        search = filters.get("search")

        if status:
            query["status"] = status
        if department:
            query["department"] = {"$regex": f"^{re.escape(department)}$", "$options": "i"}
        if village:
            query["village_tags"] = {"$elemMatch": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}
        if search:
            query["$or"] = [
                {"title": {"$regex": re.escape(search), "$options": "i"}},
                {"summary": {"$regex": re.escape(search), "$options": "i"}},
                {"description": {"$regex": re.escape(search), "$options": "i"}},
                {"department": {"$regex": re.escape(search), "$options": "i"}},
            ]

        total = self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return list(cursor), total

    def count_by_status(self):
        return {status: self.collection.count_documents({"status": status}) for status in SCHEME_STATUSES}

    def count_for_village(self, village: str):
        return self.collection.count_documents(
            {
                "status": "published",
                "village_tags": {"$elemMatch": {"$regex": f"^{re.escape(village)}$", "$options": "i"}},
            }
        )

    def recent_for_village(self, village: str, limit: int = 5):
        return list(
            self.collection.find(
                {
                    "status": "published",
                    "village_tags": {"$elemMatch": {"$regex": f"^{re.escape(village)}$", "$options": "i"}},
                }
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )


class ProjectRepository:
    def __init__(self) -> None:
        self.collection = get_collection("projects")
        self.activity_collection = get_collection("project_activities")
        self.milestone_collection = get_collection("project_milestones")
        self.progress_collection = get_collection("project_progress_updates")
        self.expenditure_collection = get_collection("project_expenditures")

    def ensure_indexes(self) -> None:
        self.collection.create_index("project_number", unique=True)
        self.collection.create_index([("status", ASCENDING), ("workflow_stage", ASCENDING)])
        self.collection.create_index([("villages", ASCENDING), ("district", ASCENDING), ("state", ASCENDING)])
        self.collection.create_index([("owner.id", ASCENDING)])
        self.collection.create_index([("responsible_users.id", ASCENDING)])
        self.activity_collection.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        self.milestone_collection.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        self.progress_collection.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])
        self.expenditure_collection.create_index([("project_id", ASCENDING), ("created_at", DESCENDING)])

    def create(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.collection.insert_one(payload)
        return self.find_by_id(result.inserted_id)

    def find_by_id(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return None
        return self.collection.find_one({"_id": object_id})

    def update_by_id(self, project_id, updates: dict):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return None
        payload = {**updates, "updated_at": utc_now()}
        self.collection.update_one({"_id": object_id}, {"$set": payload})
        return self.find_by_id(object_id)

    def delete_by_id(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return False
        self.activity_collection.delete_many({"project_id": object_id})
        self.milestone_collection.delete_many({"project_id": object_id})
        self.progress_collection.delete_many({"project_id": object_id})
        self.expenditure_collection.delete_many({"project_id": object_id})
        result = self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    def list_projects(self, filters: dict, page: int, page_size: int):
        query = {}
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("workflow_stage"):
            query["workflow_stage"] = filters["workflow_stage"]
        if filters.get("priority"):
            query["priority"] = filters["priority"]
        if filters.get("village"):
            query["villages"] = {"$elemMatch": {"$regex": f"^{re.escape(filters['village'])}$", "$options": "i"}}
        if filters.get("district"):
            query["district"] = {"$regex": f"^{re.escape(filters['district'])}$", "$options": "i"}
        if filters.get("state"):
            query["state"] = {"$regex": f"^{re.escape(filters['state'])}$", "$options": "i"}
        if filters.get("owner_user_id"):
            query["owner.id"] = str(filters["owner_user_id"])
        if filters.get("responsible_user_id"):
            query["responsible_users.id"] = str(filters["responsible_user_id"])
        if filters.get("search"):
            query["$or"] = [
                {"name": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"summary": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"description": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"project_number": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"category": {"$regex": re.escape(filters["search"]), "$options": "i"}},
            ]

        total = self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return list(cursor), total

    def create_activity(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.activity_collection.insert_one(payload)
        return self.activity_collection.find_one({"_id": result.inserted_id})

    def list_activities(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return []
        return list(self.activity_collection.find({"project_id": object_id}).sort("created_at", DESCENDING))

    def find_activity_by_id(self, project_id, activity_id):
        project_object_id = maybe_object_id(project_id)
        activity_object_id = maybe_object_id(activity_id)
        if project_object_id is None or activity_object_id is None:
            return None
        return self.activity_collection.find_one({"_id": activity_object_id, "project_id": project_object_id})

    def update_activity(self, project_id, activity_id, updates: dict):
        activity = self.find_activity_by_id(project_id, activity_id)
        if not activity:
            return None
        self.activity_collection.update_one(
            {"_id": activity["_id"]},
            {"$set": {**updates, "updated_at": utc_now()}},
        )
        return self.activity_collection.find_one({"_id": activity["_id"]})

    def create_milestone(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.milestone_collection.insert_one(payload)
        return self.milestone_collection.find_one({"_id": result.inserted_id})

    def list_milestones(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return []
        return list(self.milestone_collection.find({"project_id": object_id}).sort("created_at", DESCENDING))

    def find_milestone_by_id(self, project_id, milestone_id):
        project_object_id = maybe_object_id(project_id)
        milestone_object_id = maybe_object_id(milestone_id)
        if project_object_id is None or milestone_object_id is None:
            return None
        return self.milestone_collection.find_one({"_id": milestone_object_id, "project_id": project_object_id})

    def update_milestone(self, project_id, milestone_id, updates: dict):
        milestone = self.find_milestone_by_id(project_id, milestone_id)
        if not milestone:
            return None
        self.milestone_collection.update_one(
            {"_id": milestone["_id"]},
            {"$set": {**updates, "updated_at": utc_now()}},
        )
        return self.milestone_collection.find_one({"_id": milestone["_id"]})

    def create_progress_update(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.progress_collection.insert_one(payload)
        return self.progress_collection.find_one({"_id": result.inserted_id})

    def list_progress_updates(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return []
        return list(self.progress_collection.find({"project_id": object_id}).sort("created_at", DESCENDING))

    def create_expenditure(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.expenditure_collection.insert_one(payload)
        return self.expenditure_collection.find_one({"_id": result.inserted_id})

    def list_expenditures(self, project_id):
        object_id = maybe_object_id(project_id)
        if object_id is None:
            return []
        return list(self.expenditure_collection.find({"project_id": object_id}).sort("created_at", DESCENDING))

    def recalculate_budget(self, project_id):
        project = self.find_by_id(project_id)
        if not project:
            return None
        project_object_id = project["_id"]
        spent_amount = 0.0
        for item in self.expenditure_collection.find({"project_id": project_object_id}, {"amount": 1}):
            spent_amount += float(item.get("amount", 0) or 0)
        budget = project.get("budget", {})
        allocated_amount = float(budget.get("allocated_amount", 0) or 0)
        remaining_amount = allocated_amount - spent_amount
        return self.update_by_id(
            project_object_id,
            {
                "budget": {
                    **budget,
                    "allocated_amount": allocated_amount,
                    "spent_amount": round(spent_amount, 2),
                    "remaining_amount": round(remaining_amount, 2),
                }
            },
        )

    def count_by_status(self):
        return {status: self.collection.count_documents({"status": status}) for status in PROJECT_STATUSES}

    def count_by_workflow_stage(self):
        return {
            workflow_stage: self.collection.count_documents({"workflow_stage": workflow_stage})
            for workflow_stage in PROJECT_WORKFLOW_STAGES
        }

    def count_for_village(self, village: str):
        return self.collection.count_documents(
            {"villages": {"$elemMatch": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}}
        )

    def recent_for_village(self, village: str, limit: int = 5):
        return list(
            self.collection.find(
                {"villages": {"$elemMatch": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}}
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )


class FeedbackRepository:
    def __init__(self) -> None:
        self.collection = get_collection("citizen_feedback")

    def ensure_indexes(self) -> None:
        self.collection.create_index("feedback_number", unique=True)
        self.collection.create_index([("feedback_type", ASCENDING), ("status", ASCENDING)])
        self.collection.create_index([("location.village", ASCENDING), ("location.district", ASCENDING)])
        self.collection.create_index([("created_by.id", ASCENDING)])

    def create(self, document: dict):
        timestamp = utc_now()
        payload = {**document, "created_at": timestamp, "updated_at": timestamp}
        result = self.collection.insert_one(payload)
        return self.find_by_id(result.inserted_id)

    def find_by_id(self, feedback_id):
        object_id = maybe_object_id(feedback_id)
        if object_id is None:
            return None
        return self.collection.find_one({"_id": object_id})

    def update_by_id(self, feedback_id, updates: dict):
        object_id = maybe_object_id(feedback_id)
        if object_id is None:
            return None
        self.collection.update_one(
            {"_id": object_id},
            {"$set": {**updates, "updated_at": utc_now()}},
        )
        return self.find_by_id(object_id)

    def list_feedback(self, filters: dict, page: int, page_size: int):
        query = {}
        if filters.get("feedback_type"):
            query["feedback_type"] = filters["feedback_type"]
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("village"):
            query["location.village"] = {"$regex": f"^{re.escape(filters['village'])}$", "$options": "i"}
        if filters.get("district"):
            query["location.district"] = {"$regex": f"^{re.escape(filters['district'])}$", "$options": "i"}
        if filters.get("state"):
            query["location.state"] = {"$regex": f"^{re.escape(filters['state'])}$", "$options": "i"}
        if filters.get("created_by"):
            query["created_by.id"] = str(filters["created_by"])
        if filters.get("public_only"):
            query["is_public"] = True
        if filters.get("search"):
            query["$or"] = [
                {"subject": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"message": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"feedback_number": {"$regex": re.escape(filters["search"]), "$options": "i"}},
                {"category": {"$regex": re.escape(filters["search"]), "$options": "i"}},
            ]

        total = self.collection.count_documents(query)
        cursor = (
            self.collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        return list(cursor), total

    def count_by_status(self):
        return {status: self.collection.count_documents({"status": status}) for status in FEEDBACK_STATUSES}

    def count_by_type(self):
        return {feedback_type: self.collection.count_documents({"feedback_type": feedback_type}) for feedback_type in FEEDBACK_TYPES}

    def count_for_village(self, village: str):
        return self.collection.count_documents(
            {"location.village": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}
        )

    def recent_for_village(self, village: str, limit: int = 5):
        return list(
            self.collection.find(
                {"location.village": {"$regex": f"^{re.escape(village)}$", "$options": "i"}}
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )


def get_dashboard_role_allowlist():
    return {ROLE_CITIZEN, ROLE_GOVERNMENT_EMPLOYEE, ROLE_WARD_MEMBER, ROLE_ADMIN, ROLE_SUPER_ADMIN}
