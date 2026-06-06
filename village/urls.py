from django.urls import include, path

from api.views.health import HealthCheckView

urlpatterns = [
    path("", HealthCheckView.as_view(), name="root-health"),
    path("api/", include("api.urls")),
]
