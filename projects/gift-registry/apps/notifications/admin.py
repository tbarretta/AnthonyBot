from django.contrib import admin
from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["event_type", "actor", "target_user", "family", "description_short", "created_at"]
    list_filter = ["event_type", "family", "created_at"]
    search_fields = ["description", "actor__name", "target_user__name"]
    readonly_fields = ["id", "event_type", "actor", "target_user", "family", "description", "metadata", "created_at"]

    def description_short(self, obj):
        return obj.description[:80]
    description_short.short_description = "Description"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
