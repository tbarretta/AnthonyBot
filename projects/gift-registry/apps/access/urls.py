from django.urls import path
from . import views

urlpatterns = [
    path(
        "<uuid:family_id>/request/<uuid:user_id>/",
        views.request_access,
        name="request_access",
    ),
    # Email one-click links (no auth required)
    path(
        "email/<uuid:token>/<str:action>/",
        views.respond_via_email,
        name="respond_via_email",
    ),
    # In-app respond
    path(
        "respond/<uuid:access_id>/<str:action>/",
        views.respond_in_app,
        name="respond_in_app",
    ),
]
