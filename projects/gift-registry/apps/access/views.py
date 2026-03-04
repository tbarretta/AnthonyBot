from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone

from .models import WishlistAccessRequest
from apps.families.models import Family, FamilyMembership
from apps.notifications.tasks import (
    send_access_request_notification,
    send_access_response_notification,
)
from apps.notifications.models import ActivityLog


@login_required
def request_access(request, family_id, user_id):
    """Request access to another member's wishlist."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    family = get_object_or_404(Family, pk=family_id)
    target = get_object_or_404(User, pk=user_id)

    # Both must be in the same family
    if not FamilyMembership.objects.filter(user=request.user, family=family).exists():
        raise Http404
    if not FamilyMembership.objects.filter(user=target, family=family).exists():
        raise Http404

    # Can't request your own wishlist
    if request.user == target:
        raise Http404

    # Check for existing request — permanent once decided
    existing = WishlistAccessRequest.objects.filter(
        from_user=request.user, to_user=target, family=family
    ).first()
    if existing:
        messages.warning(request, "You have already requested access to this wishlist.")
        return redirect("family_detail", family_id=family_id)

    if request.method == "POST":
        access_req = WishlistAccessRequest.objects.create(
            from_user=request.user,
            to_user=target,
            family=family,
        )
        send_access_request_notification.delay(str(access_req.id))
        ActivityLog.log(
            event_type="access_requested",
            actor=request.user,
            target_user=target,
            family=family,
            description=f"{request.user.name} requested access to {target.name}'s wishlist in {family.name}",
        )
        messages.success(request, f"Access request sent to {target.name}.")
        return redirect("family_detail", family_id=family_id)

    return render(request, "access/confirm_request.html", {
        "target": target,
        "family": family,
    })


def respond_via_email(request, token, action):
    """One-click accept/deny from email — no login required."""
    access_req = get_object_or_404(WishlistAccessRequest, token=token, status="pending")

    if action == "approve":
        access_req.approve()
        send_access_response_notification.delay(str(access_req.id), "approved")
        ActivityLog.log(
            event_type="access_approved",
            actor=access_req.to_user,
            target_user=access_req.from_user,
            family=access_req.family,
            description=f"{access_req.to_user.name} approved access for {access_req.from_user.name}",
        )
        return render(request, "access/response_confirmed.html", {
            "action": "approved",
            "requester": access_req.from_user,
        })
    elif action == "deny":
        access_req.deny()
        send_access_response_notification.delay(str(access_req.id), "denied")
        ActivityLog.log(
            event_type="access_denied",
            actor=access_req.to_user,
            target_user=access_req.from_user,
            family=access_req.family,
            description=f"{access_req.to_user.name} denied access for {access_req.from_user.name}",
        )
        return render(request, "access/response_confirmed.html", {
            "action": "denied",
            "requester": access_req.from_user,
        })
    raise Http404


@login_required
def respond_in_app(request, access_id, action):
    """Accept/deny from within the app."""
    access_req = get_object_or_404(
        WishlistAccessRequest, pk=access_id, to_user=request.user, status="pending"
    )

    if action == "approve":
        access_req.approve()
        send_access_response_notification.delay(str(access_req.id), "approved")
        messages.success(request, f"You've granted {access_req.from_user.name} access to your wishlist.")
    elif action == "deny":
        access_req.deny()
        send_access_response_notification.delay(str(access_req.id), "denied")
        messages.info(request, f"You've declined {access_req.from_user.name}'s request.")

    return redirect("family_detail", family_id=access_req.family_id)
