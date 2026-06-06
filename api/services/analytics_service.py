import re

from ..repositories import ComplaintRepository, FeedbackRepository, ProjectRepository, SchemeRepository
from ..utils import serialize_value


class AnalyticsService:
    def __init__(self) -> None:
        self.project_repository = ProjectRepository()
        self.complaint_repository = ComplaintRepository()
        self.feedback_repository = FeedbackRepository()
        self.scheme_repository = SchemeRepository()

    def _regex_equals(self, value: str):
        return {"$regex": f"^{re.escape(value)}$", "$options": "i"}

    def _find_projects(self, village: str | None = None, district: str | None = None, state: str | None = None):
        query = {}
        if village:
            query["villages"] = {"$elemMatch": self._regex_equals(village)}
        if district:
            query["district"] = self._regex_equals(district)
        if state:
            query["state"] = self._regex_equals(state)
        return list(self.project_repository.collection.find(query).sort("created_at", -1))

    def _find_complaints(self, village: str | None = None, district: str | None = None, state: str | None = None):
        query = {}
        if village:
            query["$and"] = query.get("$and", [])
            query["$and"].append(
                {
                    "$or": [
                        {"location.village": self._regex_equals(village)},
                        {"village": self._regex_equals(village)},
                    ]
                }
            )
        if district:
            query["$and"] = query.get("$and", [])
            query["$and"].append(
                {
                    "$or": [
                        {"location.district": self._regex_equals(district)},
                        {"district": self._regex_equals(district)},
                    ]
                }
            )
        if state:
            query["$and"] = query.get("$and", [])
            query["$and"].append(
                {
                    "$or": [
                        {"location.state": self._regex_equals(state)},
                        {"state": self._regex_equals(state)},
                    ]
                }
            )
        return list(self.complaint_repository.collection.find(query).sort("created_at", -1))

    def _find_feedback(self, village: str | None = None, district: str | None = None, state: str | None = None):
        query = {}
        if village:
            query["location.village"] = self._regex_equals(village)
        if district:
            query["location.district"] = self._regex_equals(district)
        if state:
            query["location.state"] = self._regex_equals(state)
        return list(self.feedback_repository.collection.find(query).sort("created_at", -1))

    def _find_schemes(self, village: str | None = None):
        query = {"status": "published"}
        if village:
            query["village_tags"] = {"$elemMatch": self._regex_equals(village)}
        return list(self.scheme_repository.collection.find(query).sort("created_at", -1))

    def _sum_budget(self, projects: list[dict]):
        allocated_total = 0.0
        spent_total = 0.0
        remaining_total = 0.0
        for project in projects:
            budget = project.get("budget", {})
            allocated_total += float(budget.get("allocated_amount", 0) or 0)
            spent_total += float(budget.get("spent_amount", 0) or 0)
            remaining_total += float(budget.get("remaining_amount", 0) or 0)
        return {
            "allocated_total": round(allocated_total, 2),
            "spent_total": round(spent_total, 2),
            "remaining_total": round(remaining_total, 2),
        }

    def _average_progress(self, projects: list[dict]):
        if not projects:
            return 0
        total_progress = sum(float(project.get("progress_percent", 0) or 0) for project in projects)
        return round(total_progress / len(projects), 2)

    def _count_by_key(self, items: list[dict], key_name: str):
        counts = {}
        for item in items:
            key_value = item.get(key_name) or "unknown"
            counts[key_value] = counts.get(key_value, 0) + 1
        return counts

    def _project_milestone_summary(self, projects: list[dict]):
        project_ids = [project["_id"] for project in projects]
        if not project_ids:
            return {"total": 0, "achieved": 0}
        total = self.project_repository.milestone_collection.count_documents({"project_id": {"$in": project_ids}})
        achieved = self.project_repository.milestone_collection.count_documents(
            {"project_id": {"$in": project_ids}, "status": "achieved"}
        )
        return {"total": total, "achieved": achieved}

    def build_village_dashboard(self, village: str, district: str | None = None, state: str | None = None):
        projects = self._find_projects(village=village, district=district, state=state)
        complaints = self._find_complaints(village=village, district=district, state=state)
        feedback_items = self._find_feedback(village=village, district=district, state=state)
        schemes = self._find_schemes(village=village)

        budget_summary = self._sum_budget(projects)
        milestone_summary = self._project_milestone_summary(projects)

        return {
            "village": village,
            "district": district or (projects[0].get("district") if projects else None) or (
                complaints[0].get("location", {}).get("district") if complaints else None
            ),
            "state": state or (projects[0].get("state") if projects else None) or (
                complaints[0].get("location", {}).get("state") if complaints else None
            ),
            "projects": {
                "total": len(projects),
                "by_status": self._count_by_key(projects, "status"),
                "by_workflow_stage": self._count_by_key(projects, "workflow_stage"),
                "average_progress_percent": self._average_progress(projects),
                "milestones": milestone_summary,
                "recent": [serialize_value(item) for item in projects[:5]],
            },
            "budgets": budget_summary,
            "complaints": {
                "total": len(complaints),
                "by_status": self._count_by_key(complaints, "status"),
                "recent": [serialize_value(item) for item in complaints[:5]],
            },
            "feedback": {
                "total": len(feedback_items),
                "by_status": self._count_by_key(feedback_items, "status"),
                "by_type": self._count_by_key(feedback_items, "feedback_type"),
                "recent": [serialize_value(item) for item in feedback_items[:5]],
            },
            "schemes": {
                "total": len(schemes),
                "recent": [serialize_value(item) for item in schemes[:5]],
            },
            "charts": {
                "project_status": [{"label": key, "value": value} for key, value in self._count_by_key(projects, "status").items()],
                "complaint_status": [{"label": key, "value": value} for key, value in self._count_by_key(complaints, "status").items()],
                "feedback_type": [{"label": key, "value": value} for key, value in self._count_by_key(feedback_items, "feedback_type").items()],
                "budget": [
                    {"label": "allocated", "value": budget_summary["allocated_total"]},
                    {"label": "spent", "value": budget_summary["spent_total"]},
                    {"label": "remaining", "value": budget_summary["remaining_total"]},
                ],
            },
        }

    def list_village_dashboards(self, search: str | None = None, district: str | None = None, state: str | None = None):
        village_names = set()

        for project in self._find_projects(district=district, state=state):
            for village in project.get("villages", []):
                village_names.add(village)

        for complaint in self._find_complaints(district=district, state=state):
            village = complaint.get("location", {}).get("village")
            if village:
                village_names.add(village)

        for feedback_item in self._find_feedback(district=district, state=state):
            village = feedback_item.get("location", {}).get("village")
            if village:
                village_names.add(village)

        for scheme in self._find_schemes():
            for village in scheme.get("village_tags", []):
                village_names.add(village)

        ordered_villages = sorted(village_names)
        if search:
            ordered_villages = [village for village in ordered_villages if search.lower() in village.lower()]

        return [self.build_village_dashboard(village, district=district, state=state) for village in ordered_villages]

    def build_reports_overview(self):
        all_projects = self._find_projects()
        all_complaints = self._find_complaints()
        all_feedback_items = self._find_feedback()
        all_schemes = self._find_schemes()
        village_dashboards = self.list_village_dashboards()

        village_performance = [
            {
                "village": item["village"],
                "project_total": item["projects"]["total"],
                "average_progress_percent": item["projects"]["average_progress_percent"],
                "budget_spent_total": item["budgets"]["spent_total"],
                "complaint_total": item["complaints"]["total"],
                "feedback_total": item["feedback"]["total"],
            }
            for item in village_dashboards
        ]
        village_performance.sort(key=lambda item: (item["project_total"], item["budget_spent_total"]), reverse=True)

        return {
            "summary": {
                "projects_total": len(all_projects),
                "complaints_total": len(all_complaints),
                "feedback_total": len(all_feedback_items),
                "schemes_total": len(all_schemes),
                "village_total": len(village_dashboards),
            },
            "projects": {
                "by_status": self._count_by_key(all_projects, "status"),
                "by_workflow_stage": self._count_by_key(all_projects, "workflow_stage"),
                "average_progress_percent": self._average_progress(all_projects),
                "budget": self._sum_budget(all_projects),
            },
            "complaints": {
                "by_status": self._count_by_key(all_complaints, "status"),
                "high_priority_total": len(
                    [item for item in all_complaints if item.get("priority") in {"high", "critical"}]
                ),
            },
            "feedback": {
                "by_status": self._count_by_key(all_feedback_items, "status"),
                "by_type": self._count_by_key(all_feedback_items, "feedback_type"),
            },
            "charts": {
                "project_status": [{"label": key, "value": value} for key, value in self._count_by_key(all_projects, "status").items()],
                "workflow_stage": [{"label": key, "value": value} for key, value in self._count_by_key(all_projects, "workflow_stage").items()],
                "complaint_status": [{"label": key, "value": value} for key, value in self._count_by_key(all_complaints, "status").items()],
                "feedback_type": [{"label": key, "value": value} for key, value in self._count_by_key(all_feedback_items, "feedback_type").items()],
            },
            "top_villages": village_performance[:10],
        }

    def build_project_report(self, village: str | None = None, district: str | None = None, state: str | None = None):
        projects = self._find_projects(village=village, district=district, state=state)
        return {
            "filters": {"village": village, "district": district, "state": state},
            "summary": {
                "total": len(projects),
                "by_status": self._count_by_key(projects, "status"),
                "by_workflow_stage": self._count_by_key(projects, "workflow_stage"),
                "average_progress_percent": self._average_progress(projects),
                "budget": self._sum_budget(projects),
                "milestones": self._project_milestone_summary(projects),
            },
            "items": [serialize_value(item) for item in projects],
        }

    def build_village_report(self, district: str | None = None, state: str | None = None):
        return {
            "filters": {"district": district, "state": state},
            "villages": self.list_village_dashboards(district=district, state=state),
        }
