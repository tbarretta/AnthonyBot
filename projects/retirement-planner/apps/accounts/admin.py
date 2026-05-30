from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Invitation


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "first_name", "last_name", "is_staff", "date_joined"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "created_by", "created_at", "expires_at", "is_used"]
    list_filter = ["used_at"]
    search_fields = ["email"]
    readonly_fields = ["token", "used_at", "used_by"]

    def is_used(self, obj):
        return obj.is_used
    is_used.boolean = True
