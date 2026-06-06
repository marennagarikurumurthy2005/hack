from rest_framework.views import APIView

from ..responses import api_response
from ..services.analytics_service import AnalyticsService


class VillageDashboardListView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analytics_service = AnalyticsService()

    def get(self, request):
        dashboards = self.analytics_service.list_village_dashboards(
            search=request.query_params.get("search"),
            district=request.query_params.get("district"),
            state=request.query_params.get("state"),
        )
        return api_response(
            data={"villages": dashboards},
            message="Village dashboards fetched successfully.",
        )


class VillageDashboardDetailView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.analytics_service = AnalyticsService()

    def get(self, request, village_name: str):
        dashboard = self.analytics_service.build_village_dashboard(
            village_name,
            district=request.query_params.get("district"),
            state=request.query_params.get("state"),
        )
        return api_response(
            data={"village_dashboard": dashboard},
            message="Village dashboard fetched successfully.",
        )
