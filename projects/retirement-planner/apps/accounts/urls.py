from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("register/<uuid:token>/", views.register, name="register"),
    path("invitations/", views.invite_list, name="invite_list"),
    path("invitations/new/", views.invite_create, name="invite_create"),
]
