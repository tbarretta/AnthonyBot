from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'created_at', 'is_approved', 'is_flagged')
    list_filter = ('is_approved', 'is_flagged', 'created_at')
    search_fields = ('author_name', 'body')
    actions = ['approve_comments', 'unapprove_comments', 'unflag_comments']

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"

    def unapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_comments.short_description = "Unapprove selected comments"

    def unflag_comments(self, request, queryset):
        queryset.update(is_flagged=False)
    unflag_comments.short_description = "Unflag selected comments (mark safe)"
