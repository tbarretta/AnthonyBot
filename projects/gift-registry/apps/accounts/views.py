from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .models import User, EmailVerificationToken, UserNotificationPreference, NewItemNotificationSubscription
from .forms import LoginForm, RegistrationForm, PasswordResetRequestForm, SetNewPasswordForm
from apps.families.models import FamilyInvitation, FamilyMembership
from apps.notifications.tasks import send_verification_email, send_password_reset_email


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get("next", "dashboard"))
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def register_view(request, token):
    """Registration via invitation token."""
    invitation = get_object_or_404(FamilyInvitation, token=token, status="pending")
    if not invitation.is_valid():
        messages.error(request, "This invitation link has expired or already been used.")
        return redirect("login")

    # If email already has an account, just add them to the family
    existing_user = User.objects.filter(email=invitation.email).first()
    if existing_user:
        membership, created = FamilyMembership.objects.get_or_create(
            user=existing_user, family=invitation.family,
            defaults={"role": "member"}
        )
        invitation.status = "accepted"
        invitation.save(update_fields=["status"])
        messages.success(request, f"You've been added to {invitation.family.name}!")
        return redirect("login")

    form = RegistrationForm(request.POST or None, initial={"email": invitation.email})
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # Create family membership
        FamilyMembership.objects.create(user=user, family=invitation.family, role="member")
        invitation.status = "accepted"
        invitation.save(update_fields=["status"])
        # Create notification prefs
        UserNotificationPreference.objects.create(user=user)
        # Send verification email
        token_obj = EmailVerificationToken.objects.create(user=user)
        send_verification_email.delay(user.id, str(token_obj.token))
        messages.success(request, "Account created! Please check your email to verify your address.")
        return redirect("verify_email_sent")

    return render(request, "accounts/register.html", {
        "form": form,
        "invitation": invitation,
    })


def verify_email_sent(request):
    return render(request, "accounts/verify_email_sent.html")


def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)
    if not token_obj.is_valid():
        messages.error(request, "This verification link has expired or already been used.")
        return redirect("login")
    token_obj.consume()
    messages.success(request, "Email verified! You can now sign in.")
    return redirect("login")


def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email=email, is_email_verified=False).first()
        if user:
            token_obj = EmailVerificationToken.objects.create(user=user)
            send_verification_email.delay(user.id, str(token_obj.token))
    messages.info(request, "If that email matches an unverified account, a new link has been sent.")
    return redirect("verify_email_sent")


def forgot_password(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email=email).first()
        if user:
            send_password_reset_email.delay(user.id)
        # Always show success — don't reveal whether email exists
        messages.success(request, "If that email has an account, a reset link has been sent.")
        return redirect("login")
    return render(request, "accounts/forgot_password.html", {"form": form})


def reset_password(request, token):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    # Implementation uses Django's built-in token generator
    # Token format: uid:token passed via email link
    try:
        uid = urlsafe_base64_decode(token.split(":")[0]).decode()
        user = User.objects.get(pk=uid)
        raw_token = token.split(":")[1]
        if not default_token_generator.check_token(user, raw_token):
            raise ValueError
    except Exception:
        messages.error(request, "This reset link is invalid or has expired.")
        return redirect("forgot_password")

    form = SetNewPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save(update_fields=["password"])
        messages.success(request, "Password updated. You can now sign in.")
        return redirect("login")
    return render(request, "accounts/reset_password.html", {"form": form})


@login_required
def dashboard(request):
    from apps.wishlist.models import WishlistItem
    from apps.access.models import WishlistAccessRequest
    from apps.families.models import FamilyMembership

    memberships = FamilyMembership.objects.filter(user=request.user).select_related("family")
    my_items = WishlistItem.objects.filter(owner=request.user, is_soft_removed=False).order_by("-desire_rating")[:3]
    pending_requests = WishlistAccessRequest.objects.filter(to_user=request.user, status="pending")

    return render(request, "accounts/dashboard.html", {
        "memberships": memberships,
        "my_items": my_items,
        "pending_requests": pending_requests,
        "item_count": WishlistItem.objects.filter(owner=request.user).count(),
        "item_limit": settings.WISHLIST_ITEM_LIMIT,
    })


@login_required
def preferences(request):
    prefs, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
    # Get family members for subscription management
    from apps.families.models import FamilyMembership
    family_members = User.objects.filter(
        family_memberships__family__in=request.user.family_memberships.values("family")
    ).exclude(pk=request.user.pk).distinct()

    subscriptions = NewItemNotificationSubscription.objects.filter(
        subscriber=request.user
    ).values_list("target_user_id", flat=True)

    if request.method == "POST":
        prefs.notify_on_access_request = "notify_on_access_request" in request.POST
        prefs.save()
        # Update item notification subscriptions
        subscribed_ids = request.POST.getlist("subscribe_to")
        NewItemNotificationSubscription.objects.filter(subscriber=request.user).delete()
        for uid in subscribed_ids:
            target = User.objects.filter(pk=uid).first()
            if target:
                NewItemNotificationSubscription.objects.get_or_create(
                    subscriber=request.user, target_user=target
                )
        messages.success(request, "Preferences saved.")
        return redirect("preferences")

    return render(request, "accounts/preferences.html", {
        "prefs": prefs,
        "family_members": family_members,
        "subscriptions": list(subscriptions),
    })
