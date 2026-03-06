from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import timedelta

THEME_CHOICES = [
    ("midnight",  "🌙 Midnight"),
    ("forest",    "🌿 Forest"),
    ("royal",     "💜 Royal"),
    ("snow",      "❄️ Snow"),
    ("blush",     "🌸 Blush"),
    ("sunshine",  "☀️ Sunshine"),
]

ROLE_CHOICES = [
    ("admin",  "Family Admin"),
    ("member", "Member"),
]


class Family(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    theme = models.CharField(max_length=30, choices=THEME_CHOICES, default="midnight")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_families",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Families"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_members(self):
        return self.memberships.select_related("user").filter(user__is_active=True)

    def get_admins(self):
        return self.memberships.filter(role="admin").select_related("user")


class FamilyMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_memberships",
    )
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "family")]
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user.name} in {self.family.name} ({self.role})"

    @property
    def is_admin(self):
        return self.role == "admin"


class FamilyInvitation(models.Model):
    STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("accepted", "Accepted"),
        ("expired",  "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name="invitations")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
    )
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invite to {self.family.name} for {self.email}"

    def is_valid(self):
        return self.status == "pending" and timezone.now() < self.expires_at
