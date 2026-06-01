from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/",  views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("register/<uuid:token>/", views.register, name="register"),

    # Account settings
    path("settings/", views.account_settings, name="settings"),

    # Password change (logged-in users)
    path("password/change/",
         auth_views.PasswordChangeView.as_view(
             template_name="accounts/password_change.html",
             success_url="/accounts/password/change/done/",
         ),
         name="password_change"),
    path("password/change/done/",
         auth_views.PasswordChangeDoneView.as_view(
             template_name="accounts/password_change_done.html",
         ),
         name="password_change_done"),

    # Password reset (unauthenticated)
    path("password/reset/",
         auth_views.PasswordResetView.as_view(
             template_name="accounts/password_reset.html",
             email_template_name="accounts/email/password_reset.txt",
             subject_template_name="accounts/email/password_reset_subject.txt",
             success_url="/accounts/password/reset/done/",
         ),
         name="password_reset"),
    path("password/reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="accounts/password_reset_done.html",
         ),
         name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(
             template_name="accounts/password_reset_confirm.html",
             success_url="/accounts/password/reset/complete/",
         ),
         name="password_reset_confirm"),
    path("password/reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="accounts/password_reset_complete.html",
         ),
         name="password_reset_complete"),

    # Invitations (staff only)
    path("invitations/",     views.invite_list,   name="invite_list"),
    path("invitations/new/", views.invite_create, name="invite_create"),
]
