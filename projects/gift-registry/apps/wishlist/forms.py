from django import forms
from .models import WishlistItem, SOFT_REMOVE_REASONS


class WishlistItemForm(forms.ModelForm):
    # Family visibility is handled separately in the view via checkboxes
    class Meta:
        model = WishlistItem
        fields = ["name", "description", "price", "desire_rating", "purchase_link", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Sony WH-1000XM5 Headphones"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Tell family members what you love about this..."}),
            "price": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01", "min": "0"}),
            "desire_rating": forms.RadioSelect(choices=[(i, "★" * i) for i in range(1, 6)]),
            "purchase_link": forms.URLInput(attrs={"placeholder": "https://..."}),
        }
        help_texts = {
            "desire_rating": "1 = Nice to have · 5 = Really want this!",
            "purchase_link": "Optional — helps family members find the right item.",
            "image": "Optional — JPG or PNG, max 5MB.",
        }


class SoftRemoveForm(forms.Form):
    reason = forms.ChoiceField(
        choices=SOFT_REMOVE_REASONS,
        widget=forms.RadioSelect,
        label="Why are you removing this?",
    )
