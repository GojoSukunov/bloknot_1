from django.urls import include, path
from rest_framework import routers

from .views import (ChangePasswordView, DealDetailView, DealListCreateView, LoginView, LogoutView, MeView,
                    NoteViewSet, RefreshView, RegisterView, TasksViewSet)

# SimpleRouter — без публичного корневого индекса API
router = routers.SimpleRouter()
router.register(r"tasks", TasksViewSet, basename="tasks")
router.register(r"notes", NoteViewSet, basename="note")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password/", ChangePasswordView.as_view(), name="change-password"),
    path("me/", MeView.as_view(), name="me"),
    path("deals/", DealListCreateView.as_view(), name="deal-list"),
    path("deals/<int:pk>/", DealDetailView.as_view(), name="deal-detail"),
    path("", include(router.urls)),
]
