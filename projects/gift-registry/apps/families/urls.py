from django.urls import path
from . import views

urlpatterns = [
    path("<uuid:family_id>/", views.family_detail, name="family_detail"),
    path("<uuid:family_id>/admin/", views.family_admin, name="family_admin"),
]
