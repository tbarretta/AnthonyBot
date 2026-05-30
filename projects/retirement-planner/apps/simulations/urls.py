from django.urls import path
from . import views

app_name = "simulations"

urlpatterns = [
    path("", views.scenario_list, name="list"),
    path("new/", views.scenario_create, name="create"),
    path("<int:pk>/", views.scenario_detail, name="detail"),
    path("<int:pk>/edit/", views.scenario_edit, name="edit"),
    path("<int:pk>/delete/", views.scenario_delete, name="delete"),
    path("<int:pk>/run/", views.run_simulation, name="run"),
    path("results/<int:pk>/", views.result_detail, name="result_detail"),
    path("results/<int:pk>/status/", views.result_status, name="result_status"),
]
