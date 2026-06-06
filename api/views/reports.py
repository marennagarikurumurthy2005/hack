from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView

from ..constants import ROLE_ADMIN
from ..permissions import has_role
from ..responses import api_response
from ..services.analytics_service import AnalyticsService


class ReportsOverviewView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analytics_service = AnalyticsService()

    def get(self, request):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can access reports.")
        return api_response(
            data=self.analytics_service.build_reports_overview(),
            message="Reports overview fetched successfully.",
        )


class ProjectReportsView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analytics_service = AnalyticsService()

    def get(self, request):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can access project reports.")
        return api_response(
            data=self.analytics_service.build_project_report(
                village=request.query_params.get("village"),
                district=request.query_params.get("district"),
                state=request.query_params.get("state"),
            ),
            message="Project report fetched successfully.",
        )


class VillageReportsView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analytics_service = AnalyticsService()

    def get(self, request):
        if not has_role(request.user, {ROLE_ADMIN}):
            raise PermissionDenied("Only admins and super admins can access village reports.")
        return api_response(
            data=self.analytics_service.build_village_report(
                district=request.query_params.get("district"),
                state=request.query_params.get("state"),
            ),
            message="Village report fetched successfully.",
        )
