from django.contrib import admin
from .models import WishlistItem, ItemFamilyVisibility, PurchasedItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "price", "desire_rating", "is_soft_removed", "is_purchased", "created_at"]
    list_filter = ["is_soft_removed", "desire_rating"]
    search_fields = ["name", "owner__name", "owner__email"]
    readonly_fields = ["created_at", "updated_at"]

    def is_purchased(self, obj):
        return obj.is_purchased
    is_purchased.boolean = True


@admin.register(PurchasedItem)
class PurchasedItemAdmin(admin.ModelAdmin):
    list_display = ["item", "purchased_by", "purchased_at"]
    readonly_fields = ["purchased_at"]


admin.site.register(ItemFamilyVisibility)
