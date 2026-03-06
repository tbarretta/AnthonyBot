from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import Http404

from .models import WishlistItem, ItemFamilyVisibility, PurchasedItem
from .forms import WishlistItemForm, SoftRemoveForm
from apps.families.models import Family, FamilyMembership
from apps.access.models import WishlistAccessRequest
from apps.notifications.tasks import send_new_item_notification


@login_required
def my_wishlist(request):
    items = WishlistItem.objects.filter(owner=request.user).prefetch_related(
        "visible_to_families"
    )
    memberships = FamilyMembership.objects.filter(user=request.user).select_related("family")
    item_count = items.count()

    return render(request, "wishlist/my_wishlist.html", {
        "items": items,
        "item_count": item_count,
        "item_limit": settings.WISHLIST_ITEM_LIMIT,
        "can_add": item_count < settings.WISHLIST_ITEM_LIMIT,
        "memberships": memberships,
    })


@login_required
def add_item(request):
    if not request.user.can_add_items:
        messages.error(request, f"You've reached the {settings.WISHLIST_ITEM_LIMIT}-item limit.")
        return redirect("my_wishlist")

    memberships = FamilyMembership.objects.filter(user=request.user).select_related("family")
    form = WishlistItemForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        # Set family visibility
        selected_family_ids = request.POST.getlist("visible_to_families")
        if not selected_family_ids:
            # Default: visible to all families user belongs to
            selected_family_ids = [str(m.family_id) for m in memberships]
        for fid in selected_family_ids:
            family = Family.objects.filter(pk=fid).first()
            if family and memberships.filter(family=family).exists():
                ItemFamilyVisibility.objects.get_or_create(item=item, family=family)
        # Notify subscribers
        send_new_item_notification.delay(str(item.id))
        messages.success(request, f'"{item.name}" added to your wishlist.')
        return redirect("my_wishlist")

    return render(request, "wishlist/item_form.html", {
        "form": form,
        "memberships": memberships,
        "action": "Add",
    })


@login_required
def edit_item(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, owner=request.user)
    memberships = FamilyMembership.objects.filter(user=request.user).select_related("family")
    current_visibility = item.visible_to_families.values_list("id", flat=True)

    form = WishlistItemForm(request.POST or None, request.FILES or None, instance=item)

    if request.method == "POST" and form.is_valid():
        form.save()
        # Update family visibility
        ItemFamilyVisibility.objects.filter(item=item).delete()
        selected_family_ids = request.POST.getlist("visible_to_families")
        for fid in selected_family_ids:
            family = Family.objects.filter(pk=fid).first()
            if family and memberships.filter(family=family).exists():
                ItemFamilyVisibility.objects.get_or_create(item=item, family=family)
        messages.success(request, f'"{item.name}" updated.')
        return redirect("my_wishlist")

    return render(request, "wishlist/item_form.html", {
        "form": form,
        "item": item,
        "memberships": memberships,
        "current_visibility": list(current_visibility),
        "action": "Edit",
    })


@login_required
def delete_item(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, owner=request.user)
    if request.method == "POST":
        name = item.name
        item.delete()
        messages.success(request, f'"{name}" deleted.')
    return redirect("my_wishlist")


@login_required
def soft_remove_item(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, owner=request.user)
    form = SoftRemoveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item.soft_remove(form.cleaned_data["reason"])
        messages.success(request, f'"{item.name}" marked as no longer needed.')
        return redirect("my_wishlist")
    return render(request, "wishlist/soft_remove.html", {"form": form, "item": item})


@login_required
def undo_soft_remove(request, item_id):
    item = get_object_or_404(WishlistItem, pk=item_id, owner=request.user)
    if request.method == "POST":
        item.undo_soft_remove()
        messages.success(request, f'"{item.name}" is back on your wishlist.')
    return redirect("my_wishlist")


@login_required
def view_member_wishlist(request, user_id, family_id):
    """View another member's wishlist — access-controlled."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    owner = get_object_or_404(User, pk=user_id)
    family = get_object_or_404(Family, pk=family_id)

    # Both must be in the same family
    if not FamilyMembership.objects.filter(user=request.user, family=family).exists():
        raise Http404
    if not FamilyMembership.objects.filter(user=owner, family=family).exists():
        raise Http404

    # Check access is granted
    access = WishlistAccessRequest.objects.filter(
        from_user=request.user, to_user=owner, family=family, status="approved"
    ).first()
    if not access:
        pending = WishlistAccessRequest.objects.filter(
            from_user=request.user, to_user=owner, family=family, status="pending"
        ).exists()
        return render(request, "wishlist/access_required.html", {
            "owner": owner,
            "family": family,
            "pending": pending,
        })

    # Fetch items visible to this family — exclude purchase_record for owner
    items = WishlistItem.objects.filter(
        owner=owner,
        visible_to_families=family,
    ).prefetch_related("purchase_record")

    return render(request, "wishlist/member_wishlist.html", {
        "owner": owner,
        "family": family,
        "items": items,
    })


@login_required
def view_item_detail(request, user_id, family_id, item_id):
    """Item detail — with Mark Purchased action."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    owner = get_object_or_404(User, pk=user_id)
    family = get_object_or_404(Family, pk=family_id)
    item = get_object_or_404(WishlistItem, pk=item_id, owner=owner, visible_to_families=family)

    # Verify access
    access = WishlistAccessRequest.objects.filter(
        from_user=request.user, to_user=owner, family=family, status="approved"
    ).first()
    if not access:
        raise Http404

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "purchase":
            PurchasedItem.objects.get_or_create(item=item, defaults={"purchased_by": request.user})
            messages.success(request, f'"{item.name}" marked as purchased!')
        elif action == "unpurchase":
            # Only the person who marked it can undo it
            record = PurchasedItem.objects.filter(item=item, purchased_by=request.user).first()
            if record:
                record.delete()
                messages.success(request, "Purchase mark removed.")
        return redirect("view_item_detail", user_id=user_id, family_id=family_id, item_id=item_id)

    purchased_by_me = PurchasedItem.objects.filter(item=item, purchased_by=request.user).exists()

    return render(request, "wishlist/item_detail.html", {
        "owner": owner,
        "family": family,
        "item": item,
        "purchased_by_me": purchased_by_me,
    })
