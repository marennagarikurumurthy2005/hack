from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ..mongodb import ping_database
from ..responses import api_response


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            ping_database()
            return api_response(
                data={
                    "service": "village-governance-api",
                    "status": "healthy",
                    "mongodb": "connected",
                }
            )
        except Exception as exc:
            return api_response(
                data={
                    "service": "village-governance-api",
                    "status": "degraded",
                    "mongodb": "unavailable",
                    "reason": str(exc),
                },
                message="Service is reachable but MongoDB is not available.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
