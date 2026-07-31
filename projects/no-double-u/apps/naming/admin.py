from django.contrib import admin
from .models import NameSuggestion, Vote

@admin.register(NameSuggestion)
class NameSuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'submitted_by', 'vote_count', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('name', 'description')
    actions = ['approve_suggestions', 'unapprove_suggestions']

    def approve_suggestions(self, request, queryset):
        queryset.update(is_approved=True)
    approve_suggestions.short_description = "Approve selected suggestions"

    def unapprove_suggestions(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_suggestions.short_description = "Unapprove selected suggestions"

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('suggestion', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('suggestion__name', 'user__username')