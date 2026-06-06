from django.urls import include, path

from api.views.health import RootHealthCheckView

urlpatterns = [
    path("", RootHealthCheckView.as_view(), name="root-health"),
    path("api/", include("api.urls")),
]
