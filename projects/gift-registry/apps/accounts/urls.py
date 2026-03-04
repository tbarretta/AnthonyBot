from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/<uuid:token>/", views.register_view, name="register"),
    path("verify/sent/", views.verify_email_sent, name="verify_email_sent"),
    path("verify/<uuid:token>/", views.verify_email, name="verify_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<str:token>/", views.reset_password, name="reset_password"),
    path("preferences/", views.preferences, name="preferences"),
]
