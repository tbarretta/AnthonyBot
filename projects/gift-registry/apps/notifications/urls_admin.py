from django.urls import path
from . import views

urlpatterns = [
    path("", views.master_admin, name="master_admin"),
    path("create-family/", views.create_family, name="create_family"),
    path("delete-family/<uuid:family_id>/", views.delete_family, name="delete_family"),
    path("reset-password/", views.admin_reset_password, name="admin_reset_password"),
    path("reset-access/<uuid:access_id>/", views.admin_reset_access, name="admin_reset_access"),
]
