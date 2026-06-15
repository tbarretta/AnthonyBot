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
         views.CustomPasswordChangeView.as_view(),
         name="password_change"),
    path("password/change/done/",
         auth_views.PasswordChangeDoneView.as_view(
             template_name="accounts/password_change_done.html",
         ),
         name="password_change_done"),

    # Password reset (unauthenticated)
    path("password/reset/",
         views.CustomPasswordResetView.as_view(),
         name="password_reset"),
    path("password/reset/done/",
         auth_views.PasswordResetDoneView.as_view(
             template_name="accounts/password_reset_done.html",
         ),
         name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/",
         views.CustomPasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
    path("password/reset/complete/",
         auth_views.PasswordResetCompleteView.as_view(
             template_name="accounts/password_reset_complete.html",
         ),
         name="password_reset_complete"),

    # Invitations (staff only)
    path("invitations/",     views.invite_list,   name="invite_list"),
    path("invitations/new/", views.invite_create, name="invite_create"),
    path("invitations/<int:pk>/delete/", views.invite_delete, name="invite_delete"),

    # Admin panel
    path("admin-panel/",                            views.admin_dashboard,           name="admin_dashboard"),
    path("admin-panel/users/",                      views.admin_user_list,           name="admin_user_list"),
    path("admin-panel/users/<int:pk>/delete/",      views.admin_user_delete,         name="admin_user_delete"),
    path("admin-panel/users/<int:pk>/reset/",       views.admin_user_reset_password, name="admin_user_reset_password"),
    path("admin-panel/audit/",                      views.admin_audit_log,           name="admin_audit_log"),
]
