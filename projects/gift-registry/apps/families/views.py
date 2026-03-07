from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.db.models import Count

from .models import Family, FamilyMembership, FamilyInvitation, AdminTransferRequest
from apps.access.models import WishlistAccessRequest
from apps.notifications.tasks import send_invitation_email, send_admin_transfer_email
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
        is_my_managed = m.user.is_managed and m.user.guardian_id == request.user.pk
        members_with_state.append({
            "membership": m,
            "access_request": req,
            "access_status": req.status if req else None,
            "is_my_managed": is_my_managed,
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

    viewer_membership = FamilyMembership.objects.filter(
        user=request.user, family=family
    ).first()

    return render(request, "families/family_detail.html", {
        "family": family,
        "members_with_state": members_with_state,
        "received_requests": received,
        "viewer_is_admin": viewer_membership.is_admin if viewer_membership else False,
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

        elif action == "resend_invite":
            inv_id = request.POST.get("invitation_id")
            inv = FamilyInvitation.objects.filter(pk=inv_id, family=family, status="pending").first()
            if inv:
                inv.resend()
                send_invitation_email.delay(str(inv.id))
                messages.success(request, f"Invitation resent to {inv.email}.")

        return redirect("family_admin", family_id=family_id)

    pending_transfer = AdminTransferRequest.objects.filter(
        family=family, from_user=request.user, status="pending"
    ).first()

    return render(request, "families/family_admin.html", {
        "family": family,
        "memberships": memberships,
        "pending_invitations": pending_invitations,
        "theme_choices": THEME_CHOICES,
        "pending_transfer": pending_transfer,
    })


@login_required
def initiate_admin_transfer(request, family_id, user_id):
    """Show transfer warning (GET) and create the transfer request (POST).
    Accessible to both the current Family Admin and the Master Admin.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    family = get_object_or_404(Family, pk=family_id)
    is_master_admin_action = request.user.is_master_admin

    if not is_master_admin_action:
        _require_family_admin(request.user, family)

    to_user = get_object_or_404(User, pk=user_id)

    # Target must be a member of the same family and not self
    if not FamilyMembership.objects.filter(user=to_user, family=family).exists():
        raise Http404
    if to_user == request.user:
        raise Http404

    if request.method == "POST":
        # Cancel any existing pending transfer for this family
        AdminTransferRequest.objects.filter(family=family, status="pending").update(status="cancelled")

        transfer = AdminTransferRequest.objects.create(
            family=family,
            from_user=request.user,
            to_user=to_user,
        )
        send_admin_transfer_email.delay(str(transfer.id))
        messages.success(
            request,
            f"Transfer request sent to {to_user.name}. They must accept via email before the change takes effect."
        )
        if is_master_admin_action:
            return redirect("master_admin_family", family_id=family_id)
        return redirect("family_admin", family_id=family_id)

    cancel_url = (
        "master_admin_family" if is_master_admin_action else "family_admin"
    )
    return render(request, "families/confirm_admin_transfer.html", {
        "family": family,
        "to_user": to_user,
        "is_master_admin_action": is_master_admin_action,
        "cancel_url_name": cancel_url,
    })


def respond_admin_transfer(request, token):
    """Email link handler — show accept/decline page (GET), execute on POST."""
    transfer = get_object_or_404(AdminTransferRequest, token=token, status="pending")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "accept":
            transfer.accept()
            return render(request, "families/admin_transfer_response.html", {
                "action": "accepted",
                "family": transfer.family,
                "from_user": transfer.from_user,
            })
        elif action == "decline":
            transfer.decline()
            return render(request, "families/admin_transfer_response.html", {
                "action": "declined",
                "family": transfer.family,
                "from_user": transfer.from_user,
            })
        raise Http404

    return render(request, "families/respond_admin_transfer.html", {
        "transfer": transfer,
    })
