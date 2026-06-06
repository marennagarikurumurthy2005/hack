from django.urls import path

from .views.auth import ChangePasswordView, LoginView, LogoutView, MeView, RegisterView
from .views.complaints import (
    ComplaintAssignView,
    ComplaintDetailUpdateView,
    ComplaintListCreateView,
    ComplaintProgressListCreateView,
)
from .views.dashboard import DashboardStatsView
from .views.feedback import CitizenFeedbackDetailView, CitizenFeedbackListCreateView, CitizenFeedbackRespondView
from .views.health import HealthCheckView
from .views.projects import (
    ProjectActivityDetailView,
    ProjectActivityListCreateView,
    ProjectBudgetUpdateView,
    ProjectDetailView,
    ProjectExpenditureListCreateView,
    ProjectListCreateView,
    ProjectMilestoneDetailView,
    ProjectMilestoneListCreateView,
    ProjectProgressListCreateView,
)
from .views.reports import ProjectReportsView, ReportsOverviewView, VillageReportsView
from .views.schemes import SchemeDetailView, SchemeListCreateView
from .views.uploads import ImageUploadView
from .views.users import PendingUserListView, UserDetailView, UserListView, UserRoleUpdateView, UserVerificationView
from .views.villages import VillageDashboardDetailView, VillageDashboardListView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/pending/", PendingUserListView.as_view(), name="pending-user-list"),
    path("users/<str:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<str:user_id>/verification/", UserVerificationView.as_view(), name="user-verification"),
    path("users/<str:user_id>/role/", UserRoleUpdateView.as_view(), name="user-role-update"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list-create"),
    path("projects/<str:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<str:project_id>/activities/", ProjectActivityListCreateView.as_view(), name="project-activity-list-create"),
    path("projects/<str:project_id>/activities/<str:activity_id>/", ProjectActivityDetailView.as_view(), name="project-activity-detail"),
    path("projects/<str:project_id>/milestones/", ProjectMilestoneListCreateView.as_view(), name="project-milestone-list-create"),
    path("projects/<str:project_id>/milestones/<str:milestone_id>/", ProjectMilestoneDetailView.as_view(), name="project-milestone-detail"),
    path("projects/<str:project_id>/progress/", ProjectProgressListCreateView.as_view(), name="project-progress"),
    path("projects/<str:project_id>/budget/", ProjectBudgetUpdateView.as_view(), name="project-budget-update"),
    path("projects/<str:project_id>/expenditures/", ProjectExpenditureListCreateView.as_view(), name="project-expenditures"),
    path("complaints/", ComplaintListCreateView.as_view(), name="complaint-list-create"),
    path("complaints/<str:complaint_id>/", ComplaintDetailUpdateView.as_view(), name="complaint-detail-update"),
    path("complaints/<str:complaint_id>/assign/", ComplaintAssignView.as_view(), name="complaint-assign"),
    path("complaints/<str:complaint_id>/progress/", ComplaintProgressListCreateView.as_view(), name="complaint-progress"),
    path("feedback/", CitizenFeedbackListCreateView.as_view(), name="feedback-list-create"),
    path("feedback/<str:feedback_id>/", CitizenFeedbackDetailView.as_view(), name="feedback-detail"),
    path("feedback/<str:feedback_id>/respond/", CitizenFeedbackRespondView.as_view(), name="feedback-respond"),
    path("schemes/", SchemeListCreateView.as_view(), name="scheme-list-create"),
    path("schemes/<str:scheme_id>/", SchemeDetailView.as_view(), name="scheme-detail"),
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("villages/dashboard/", VillageDashboardListView.as_view(), name="village-dashboard-list"),
    path("villages/<str:village_name>/dashboard/", VillageDashboardDetailView.as_view(), name="village-dashboard-detail"),
    path("reports/overview/", ReportsOverviewView.as_view(), name="reports-overview"),
    path("reports/projects/", ProjectReportsView.as_view(), name="project-reports"),
    path("reports/villages/", VillageReportsView.as_view(), name="village-reports"),
    path("uploads/images/", ImageUploadView.as_view(), name="image-upload"),
]
