from django.contrib import admin
from .models import Comment

class IsTopicFilter(admin.SimpleListFilter):
    title = 'is topic'
    parameter_name = 'is_topic'

    def lookups(self, request, model_admin):
        return (
            ('Yes', 'Yes'),
            ('No', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.filter(parent__isnull=True)
        if self.value() == 'No':
            return queryset.filter(parent__isnull=False)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'is_topic', 'created_at', 'is_approved', 'is_flagged')
    list_filter = ('is_approved', 'is_flagged', IsTopicFilter, 'created_at')
    search_fields = ('author_name', 'body')
    actions = ['approve_comments', 'unapprove_comments', 'unflag_comments']
    filter_horizontal = ('flagged_by',)
    
    def is_topic(self, obj):
        return obj.parent is None
    is_topic.short_description = "Is Topic"
    is_topic.boolean = True

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
    approve_comments.short_description = "Approve selected comments"

    def unapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
    unapprove_comments.short_description = "Unapprove selected comments"

    def unflag_comments(self, request, queryset):
        queryset.update(is_flagged=False)
    unflag_comments.short_description = "Unflag selected comments (mark safe)"
