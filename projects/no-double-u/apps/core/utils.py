from django.contrib.auth.models import User
from django.db.models import Q

def get_moderator_emails():
    """Return a list of unique email addresses for all superusers and moderators."""
    users = User.objects.filter(
        Q(is_superuser=True) | Q(groups__name='Moderators')
    ).exclude(email='').exclude(email__isnull=True)
    
    return list(set(users.values_list('email', flat=True)))
