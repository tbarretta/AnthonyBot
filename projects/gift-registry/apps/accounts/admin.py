from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationToken, UserNotificationPreference, NewItemNotificationSubscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "name", "is_email_verified", "is_master_admin", "is_active", "created_at"]
    list_filter = ["is_master_admin", "is_email_verified", "is_active"]
    search_fields = ["email", "name"]
    ordering = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_master_admin", "is_email_verified", "groups", "user_permissions")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "name", "password1", "password2")}),
    )
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "used_at"]
    readonly_fields = ["token", "created_at", "used_at"]


admin.site.register(UserNotificationPreference)
admin.site.register(NewItemNotificationSubscription)
