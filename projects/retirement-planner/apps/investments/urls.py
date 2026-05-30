from django.urls import path
from . import views

app_name = "investments"

urlpatterns = [
    path("", views.account_list, name="list"),
    path("new/", views.account_create, name="create"),
    path("<int:pk>/edit/", views.account_edit, name="edit"),
    path("<int:pk>/delete/", views.account_delete, name="delete"),
]
