from django.db import models
from django.conf import settings
import uuid

EVENT_TYPES = [
    ("registration",      "User Registration"),
    ("invitation_sent",   "Invitation Sent"),
    ("password_reset",    "Password Reset Requested"),
    ("access_requested",  "Wishlist Access Requested"),
    ("access_approved",   "Wishlist Access Approved"),
    ("access_denied",     "Wishlist Access Denied"),
    ("item_added",        "Wishlist Item Added"),
    ("item_soft_removed", "Item Marked No Longer Needed"),
    ("email_changed",     "Email Address Changed"),
    ("account_deleted",   "Account Deleted"),
    ("admin_pw_reset",    "Admin Password Reset"),
    ("access_reset",      "Access Request Reset by Admin"),
    ("family_created",    "Family Created by Admin"),
    ("family_deleted",    "Family Deleted by Admin"),
]


class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_as_actor",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_as_target",
    )
    family = models.ForeignKey(
        "families.Family",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_log",
    )
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Activity Log Entry"
        verbose_name_plural = "Activity Log"

    def __str__(self):
        return f"[{self.event_type}] {self.description[:60]}"

    @classmethod
    def log(cls, event_type, description, actor=None, target_user=None, family=None, metadata=None):
        return cls.objects.create(
            event_type=event_type,
            actor=actor,
            target_user=target_user,
            family=family,
            description=description,
            metadata=metadata or {},
        )
