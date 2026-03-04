from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_master_admin", True)
        extra_fields.setdefault("is_email_verified", True)
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_master_admin = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def wishlist_item_count(self):
        return self.wishlist_items.count()

    @property
    def can_add_items(self):
        from django.conf import settings
        return self.wishlist_item_count < settings.WISHLIST_ITEM_LIMIT


class EmailVerificationToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self):
        from datetime import timedelta
        return self.used_at is None and (
            timezone.now() - self.created_at < timedelta(hours=24)
        )

    def consume(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
        self.user.is_email_verified = True
        self.user.save(update_fields=["is_email_verified"])


class UserNotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_prefs")
    notify_on_access_request = models.BooleanField(default=True)

    def __str__(self):
        return f"Prefs for {self.user.name}"


class NewItemNotificationSubscription(models.Model):
    """Subscriber gets notified when target_user adds a wishlist item."""
    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item_subscriptions")
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item_subscribers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("subscriber", "target_user")]

    def __str__(self):
        return f"{self.subscriber.name} → {self.target_user.name}"
