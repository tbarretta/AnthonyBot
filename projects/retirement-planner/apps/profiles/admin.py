from django.contrib import admin
from .models import UserProfile, SpouseProfile, SocialSecurityEstimate


class SpouseInline(admin.StackedInline):
    model = SpouseProfile
    extra = 0


class SSInline(admin.TabularInline):
    model = SocialSecurityEstimate
    extra = 0


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "current_age", "target_retirement_age", "filing_status", "is_setup_complete"]
    search_fields = ["user__email"]
    inlines = [SpouseInline, SSInline]

    def current_age(self, obj):
        return obj.current_age
