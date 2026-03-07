from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:family_id>/", views.family_detail, name="family_detail"),
    path("<uuid:family_id>/admin/", views.family_admin, name="family_admin"),
    path("<uuid:family_id>/transfer/<uuid:user_id>/", views.initiate_admin_transfer, name="initiate_admin_transfer"),
    path("transfer/<uuid:token>/", views.respond_admin_transfer, name="respond_admin_transfer"),
]
