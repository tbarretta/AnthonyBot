from django.contrib import admin
from .models import WishlistAccessRequest


@admin.register(WishlistAccessRequest)
class WishlistAccessRequestAdmin(admin.ModelAdmin):
    list_display = ["from_user", "to_user", "family", "status", "created_at", "responded_at"]
    list_filter = ["status", "family"]
    search_fields = ["from_user__name", "to_user__name", "family__name"]
    readonly_fields = ["token", "created_at", "responded_at"]
    actions = ["reset_to_pending"]

    def reset_to_pending(self, request, queryset):
        for obj in queryset:
            obj.reset()
        self.message_user(request, f"{queryset.count()} request(s) reset to pending.")
    reset_to_pending.short_description = "Reset selected requests (allow re-request) — Master Admin only"
