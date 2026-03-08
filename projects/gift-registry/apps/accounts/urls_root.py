from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path("", RedirectView.as_view(url="/dashboard/"), name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("help/", views.help_view, name="help"),
]
