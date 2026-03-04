from django.contrib import admin
from .models import Family, FamilyMembership, FamilyInvitation


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "theme", "created_by", "created_at"]
    search_fields = ["name"]
    list_filter = ["theme"]


@admin.register(FamilyMembership)
class FamilyMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "family", "role", "joined_at"]
    list_filter = ["role", "family"]
    search_fields = ["user__name", "user__email", "family__name"]


@admin.register(FamilyInvitation)
class FamilyInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "family", "invited_by", "status", "created_at", "expires_at"]
    list_filter = ["status", "family"]
    search_fields = ["email", "family__name"]
    readonly_fields = ["token", "created_at"]
