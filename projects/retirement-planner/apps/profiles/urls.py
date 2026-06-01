from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("setup/", views.profile_setup, name="setup"),
    path("setup/spouse/", views.spouse_setup, name="spouse_setup"),
    path("profile/edit/", views.profile_edit, name="edit"),
    path("help/", views.help_view, name="help"),
]
