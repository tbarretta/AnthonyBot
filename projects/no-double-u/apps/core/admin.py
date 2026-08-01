from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User, Group
from apps.discussion.models import Comment

admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    list_display = (
        'username', 'email', 'is_moderator_display', 'is_staff', 'is_active', 
        'comments_count', 'community_flagged_count', 
        'moderator_approved_count', 'flags_cast_count'
    )
    
    actions = ['make_moderator', 'remove_moderator']

    def is_moderator_display(self, obj):
        return obj.is_superuser or obj.groups.filter(name='Moderators').exists()
    is_moderator_display.boolean = True
    is_moderator_display.short_description = 'Is Moderator'

    def make_moderator(self, request, queryset):
        mod_group, _ = Group.objects.get_or_create(name='Moderators')
        for user in queryset:
            user.groups.add(mod_group)
    make_moderator.short_description = "Grant Moderator role (can access Mod Queue)"

    def remove_moderator(self, request, queryset):
        mod_group, _ = Group.objects.get_or_create(name='Moderators')
        for user in queryset:
            user.groups.remove(mod_group)
    remove_moderator.short_description = "Revoke Moderator role"
    
    def comments_count(self, obj):
        return Comment.objects.filter(author_name=obj.username).count()
    comments_count.short_description = "Total Comments"
    
    def community_flagged_count(self, obj):
        return Comment.objects.filter(author_name=obj.username, is_flagged=True).count()
    community_flagged_count.short_description = "Flagged by Community"
    
    def moderator_approved_count(self, obj):
        return Comment.objects.filter(author_name=obj.username, is_approved=True).count()
    moderator_approved_count.short_description = "Mod Approved"
    
    def flags_cast_count(self, obj):
        return obj.flagged_comments.count()
    flags_cast_count.short_description = "Flags Cast by User"

