from django.contrib import admin
from .models import UserProfile, SpouseProfile


class SpouseInline(admin.StackedInline):
    model = SpouseProfile
    extra = 0


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "current_age", "filing_status", "is_setup_complete"]
    search_fields = ["user__email"]
    inlines = [SpouseInline]

    def current_age(self, obj):
        return obj.current_age
