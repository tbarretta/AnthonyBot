from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


SOFT_REMOVE_REASONS = [
    ("no_longer_wanted", "No longer wanted"),
    ("already_have",     "Already have this / received as a gift"),
]


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    desire_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = Nice to have, 5 = Really want this!",
    )
    purchase_link = models.URLField(blank=True, default="")
    image = models.ImageField(upload_to="wishlist/", blank=True, null=True)

    # Soft remove
    is_soft_removed = models.BooleanField(default=False)
    soft_remove_reason = models.CharField(
        max_length=20, choices=SOFT_REMOVE_REASONS, blank=True, default=""
    )
    soft_removed_at = models.DateTimeField(null=True, blank=True)

    # Family visibility — which families can see this item
    visible_to_families = models.ManyToManyField(
        "families.Family",
        through="ItemFamilyVisibility",
        related_name="visible_items",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-desire_rating", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.name})"

    @property
    def is_purchased(self):
        return hasattr(self, "purchase_record")

    def soft_remove(self, reason):
        from django.utils import timezone
        self.is_soft_removed = True
        self.soft_remove_reason = reason
        self.soft_removed_at = timezone.now()
        self.save(update_fields=["is_soft_removed", "soft_remove_reason", "soft_removed_at"])

    def undo_soft_remove(self):
        self.is_soft_removed = False
        self.soft_remove_reason = ""
        self.soft_removed_at = None
        self.save(update_fields=["is_soft_removed", "soft_remove_reason", "soft_removed_at"])


class ItemFamilyVisibility(models.Model):
    """M2M through table: which families can see a wishlist item."""
    item = models.ForeignKey(WishlistItem, on_delete=models.CASCADE)
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE)

    class Meta:
        unique_together = [("item", "family")]

    def __str__(self):
        return f"{self.item.name} → {self.family.name}"


class ItemComment(models.Model):
    """Comments on a wishlist item — hidden from the item owner."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        WishlistItem,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    family = models.ForeignKey(
        "families.Family",
        on_delete=models.CASCADE,
        related_name="item_comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="item_comments",
    )
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author.name} on {self.item.name}"


class PurchasedItem(models.Model):
    """Records that an item has been purchased. Hidden from owner."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.OneToOneField(
        WishlistItem,
        on_delete=models.CASCADE,
        related_name="purchase_record",
    )
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchases_made",
    )
    purchased_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item.name} — purchased"
