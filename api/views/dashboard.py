from rest_framework.views import APIView

from ..permissions import IsAdminOrSuperAdmin
from ..repositories import ComplaintRepository, FeedbackRepository, ProjectRepository, SchemeRepository, UserRepository
from ..responses import api_response
from ..services.analytics_service import AnalyticsService
from ..utils import serialize_value


class DashboardStatsView(APIView):
    permission_classes = [IsAdminOrSuperAdmin]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_repository = UserRepository()
        self.complaint_repository = ComplaintRepository()
        self.feedback_repository = FeedbackRepository()
        self.project_repository = ProjectRepository()
        self.scheme_repository = SchemeRepository()
        self.analytics_service = AnalyticsService()

    def get(self, request):
        recent_complaints, _ = self.complaint_repository.list_complaints({}, 1, 5)
        recent_projects, _ = self.project_repository.list_projects({}, 1, 5)
        analytics_overview = self.analytics_service.build_reports_overview()
        dashboard_data = {
            "users": {
                "by_role": self.user_repository.count_by_role(),
                "by_verification_status": self.user_repository.count_by_verification_status(),
            },
            "projects": {
                "by_status": self.project_repository.count_by_status(),
                "by_workflow_stage": self.project_repository.count_by_workflow_stage(),
            },
            "complaints": {
                "by_status": self.complaint_repository.count_by_status(),
                "high_priority_total": self.complaint_repository.count_high_priority(),
            },
            "feedback": {
                "by_status": self.feedback_repository.count_by_status(),
                "by_type": self.feedback_repository.count_by_type(),
            },
            "schemes": {
                "by_status": self.scheme_repository.count_by_status(),
            },
            "reports_overview": analytics_overview,
            "recent_projects": [serialize_value(item) for item in recent_projects],
            "recent_complaints": [serialize_value(item) for item in recent_complaints],
        }
        return api_response(data=dashboard_data, message="Dashboard statistics fetched successfully.")
