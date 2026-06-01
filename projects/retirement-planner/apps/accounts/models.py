import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings


class AuditEvent(models.TextChoices):
    LOGIN = 'login', 'Login'
    LOGOUT = 'logout', 'Logout'
    LOGIN_FAILED = 'login_failed', 'Failed Login'
    PASSWORD_RESET_REQUEST = 'password_reset_request', 'Password Reset Requested'
    PASSWORD_RESET_COMPLETE = 'password_reset_complete', 'Password Reset Completed'
    PASSWORD_CHANGED = 'password_changed', 'Password Changed'
    INVITATION_CREATED = 'invitation_created', 'Invitation Created'
    INVITATION_USED = 'invitation_used', 'Invitation Used'
    USER_CREATED = 'user_created', 'User Created'
    USER_DELETED = 'user_deleted', 'User Deleted'
    ADMIN_PASSWORD_RESET = 'admin_password_reset', 'Admin Triggered Password Reset'


class User(AbstractUser):
    """
    Custom User model. Extends AbstractUser so we keep all standard
    Django auth machinery while being able to add fields later.
    """
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Invitation(models.Model):
    """
    Invite-only registration. Master Admin creates invitations;
    users register via the unique token link.
    """
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invitations_sent",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitation",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation → {self.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used


class AuditLog(models.Model):
    user = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events')
    user_email = models.EmailField(blank=True)   # preserve after deletion
    actor = models.ForeignKey('User', null=True, blank=True, on_delete=models.SET_NULL, related_name='admin_actions')
    event = models.CharField(max_length=50, choices=AuditEvent.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.event} {self.user_email}"
