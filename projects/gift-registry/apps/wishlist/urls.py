from django.urls import path
from . import views

urlpatterns = [
    path("", views.my_wishlist, name="my_wishlist"),
    path("add/", views.add_item, name="add_item"),
    path("<uuid:item_id>/edit/", views.edit_item, name="edit_item"),
    path("<uuid:item_id>/delete/", views.delete_item, name="delete_item"),
    path("<uuid:item_id>/soft-remove/", views.soft_remove_item, name="soft_remove_item"),
    path("<uuid:item_id>/undo-remove/", views.undo_soft_remove, name="undo_soft_remove"),
    # Viewing another member's list
    path(
        "<uuid:family_id>/member/<uuid:user_id>/",
        views.view_member_wishlist,
        name="view_member_wishlist",
    ),
    path(
        "<uuid:family_id>/member/<uuid:user_id>/item/<uuid:item_id>/",
        views.view_item_detail,
        name="view_item_detail",
    ),
]
