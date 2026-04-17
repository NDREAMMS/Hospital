from django.urls import path

from .api_prototype import (
    AssignmentCheckView,
    AssignmentCreateView,
    MetaView,
    ShiftListView,
    StaffProfileView,
    StaffDetailView,
    StaffListView,
)
from .api_drf import (
    login_view,
    me_view,
    shifts_view,
    my_assignments_view,
    my_absences_view,
)
from .planning_api import (
    PlanningGenerateView,
    PlanningPreviewView,
    PlanningValidateEditView,
    PlanningScoreView,
    PenaltyWeightsView,
)

urlpatterns = [
    path("meta/", MetaView.as_view(), name="api-meta"),
    path("staff/", StaffListView.as_view(), name="api-staff-list"),
    path("staff/<int:pk>/", StaffDetailView.as_view(), name="api-staff-detail"),
    path("staff/<int:pk>/profile/", StaffProfileView.as_view(), name="api-staff-profile"),
    path("shifts/", ShiftListView.as_view(), name="api-shifts-list"),
    path("assignments/check/", AssignmentCheckView.as_view(), name="api-assignments-check"),
    path("assignments/", AssignmentCreateView.as_view(), name="api-assignments-create"),
    path("plannings/generate/", PlanningGenerateView.as_view(), name="api-planning-generate"),
    path("plannings/preview/", PlanningPreviewView.as_view(), name="api-planning-preview"),
    path("plannings/validate-edit/", PlanningValidateEditView.as_view(), name="api-planning-validate-edit"),
    path("plannings/score/", PlanningScoreView.as_view(), name="api-planning-score"),
    path("plannings/penalty-weights/", PenaltyWeightsView.as_view(), name="api-planning-penalty-weights"),
    # Auth endpoints
    path("login/", login_view, name="api-login"),
    path("me/", me_view, name="api-me"),
    path("shifts/drf/", shifts_view, name="api-shifts-drf"),
    path("my-assignments/", my_assignments_view, name="api-my-assignments"),
    path("my-absences/", my_absences_view, name="api-my-absences"),
]
