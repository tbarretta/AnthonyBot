from django.db import models
from django.conf import settings
import uuid


class WishlistAccessRequest(models.Model):
    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("approved", "Approved"),
        ("denied",   "Denied"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_access_requests",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_access_requests",
    )
    family = models.ForeignKey(
        "families.Family",
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    # Tokenized for one-click email links (no login required)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # One request per pair per family — permanent once decided
        unique_together = [("from_user", "to_user", "family")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_user.name} → {self.to_user.name} ({self.status})"

    def approve(self):
        from django.utils import timezone
        self.status = "approved"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def deny(self):
        from django.utils import timezone
        self.status = "denied"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])

    def reset(self):
        """Master Admin only — allow re-request."""
        self.status = "pending"
        self.responded_at = None
        self.token = uuid.uuid4()
        self.save(update_fields=["status", "responded_at", "token"])
