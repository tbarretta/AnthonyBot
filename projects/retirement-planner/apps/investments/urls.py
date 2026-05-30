from django.urls import path
from . import views

app_name = "investments"

urlpatterns = [
    # Investment Accounts
    path("", views.account_list, name="list"),
    path("new/", views.account_create, name="create"),
    path("<int:pk>/edit/", views.account_edit, name="edit"),
    path("<int:pk>/delete/", views.account_delete, name="delete"),

    # Income Sources
    path("income/", views.income_source_list, name="income_list"),
    path("income/new/", views.income_source_create, name="income_create"),
    path("income/<int:pk>/edit/", views.income_source_edit, name="income_edit"),
    path("income/<int:pk>/delete/", views.income_source_delete, name="income_delete"),
]
