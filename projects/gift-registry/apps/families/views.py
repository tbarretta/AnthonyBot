from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404

from django.db.models import Count

from .models import Family, FamilyMembership, FamilyInvitation
from apps.access.models import WishlistAccessRequest
from apps.notifications.tasks import send_invitation_email
from apps.wishlist.models import WishlistItem


def _get_family_membership(user, family):
    """Return membership or 404."""
    return get_object_or_404(FamilyMembership, user=user, family=family)


def _require_family_admin(user, family):
    membership = _get_family_membership(user, family)
    if not membership.is_admin:
        raise Http404
    return membership


@login_required
def family_detail(request, family_id):
    """Family member list — with access states."""
    family = get_object_or_404(Family, pk=family_id)
    _get_family_membership(request.user, family)  # Must be a member

    memberships = family.get_members().exclude(user=request.user)

    # Build access state map for current user vs each member
    sent = WishlistAccessRequest.objects.filter(
        from_user=request.user,
        to_user__in=memberships.values("user"),
        family=family,
    ).select_related("to_user")
    sent_map = {r.to_user_id: r for r in sent}

    received = WishlistAccessRequest.objects.filter(
        to_user=request.user,
        from_user__in=memberships.values("user"),
        family=family,
        status="pending",
    ).select_related("from_user")

    members_with_state = []
    for m in memberships:
        req = sent_map.get(m.user_id)
        members_with_state.append({
            "membership": m,
            "access_request": req,
            "access_status": req.status if req else None,
        })

    # Batch-fetch wishlist item counts for approved members
    approved_user_ids = [
        entry["membership"].user_id
        for entry in members_with_state
        if entry["access_status"] == "approved"
    ]
    if approved_user_ids:
        item_counts = dict(
            WishlistItem.objects.filter(
                owner_id__in=approved_user_ids,
                is_soft_removed=False,
            )
            .values("owner_id")
            .annotate(count=Count("id"))
            .values_list("owner_id", "count")
        )
    else:
        item_counts = {}

    for entry in members_with_state:
        if entry["access_status"] == "approved":
            entry["item_count"] = item_counts.get(entry["membership"].user_id, 0)
        else:
            entry["item_count"] = None

    return render(request, "families/family_detail.html", {
        "family": family,
        "members_with_state": members_with_state,
        "received_requests": received,
    })


@login_required
def family_admin(request, family_id):
    """Family admin panel — invite members, set theme."""
    family = get_object_or_404(Family, pk=family_id)
    _require_family_admin(request.user, family)

    from .models import THEME_CHOICES
    memberships = family.get_members()
    pending_invitations = family.invitations.filter(status="pending")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "invite":
            email = request.POST.get("email", "").strip().lower()
            if email:
                existing_invite = FamilyInvitation.objects.filter(
                    family=family, email=email, status="pending"
                ).first()
                if existing_invite:
                    messages.warning(request, f"An invitation is already pending for {email}.")
                else:
                    inv = FamilyInvitation.objects.create(
                        family=family, invited_by=request.user, email=email
                    )
                    send_invitation_email.delay(str(inv.id))
                    messages.success(request, f"Invitation sent to {email}.")

        elif action == "set_theme":
            theme = request.POST.get("theme")
            valid_themes = [t[0] for t in THEME_CHOICES]
            if theme in valid_themes:
                family.theme = theme
                family.save(update_fields=["theme"])
                messages.success(request, "Theme updated.")

        elif action == "remove_member":
            member_id = request.POST.get("member_id")
            membership = FamilyMembership.objects.filter(
                family=family, user_id=member_id
            ).exclude(user=request.user).first()
            if membership:
                membership.delete()
                messages.success(request, f"{membership.user.name} removed from {family.name}.")

        return redirect("family_admin", family_id=family_id)

    return render(request, "families/family_admin.html", {
        "family": family,
        "memberships": memberships,
        "pending_invitations": pending_invitations,
        "theme_choices": THEME_CHOICES,
    })
