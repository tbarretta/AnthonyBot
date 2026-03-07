from django.shortcuts import render, redirect, get_object_or_404
from apps.families.models import FamilyMembership
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from .models import User, EmailVerificationToken, UserNotificationPreference, NewItemNotificationSubscription
from .forms import LoginForm, RegistrationForm, PasswordResetRequestForm, SetNewPasswordForm, ManagedMemberForm, ChangePasswordForm, DeleteAccountForm
from apps.families.models import FamilyInvitation
from apps.notifications.tasks import send_verification_email, send_password_reset_email


def get_active_member(request):
    """
    Returns the managed member currently being managed, or request.user.
    Validates the guardian relationship and clears stale session data.
    """
    mid = request.session.get("active_managed_member_id")
    if mid:
        try:
            return User.objects.get(pk=mid, guardian=request.user, is_managed=True)
        except User.DoesNotExist:
            request.session.pop("active_managed_member_id", None)
    return request.user


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
        # Create family membership — role comes from the invitation
        FamilyMembership.objects.create(user=user, family=invitation.family, role=invitation.role)
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

    # Managed members and their pending access requests
    managed_members = request.user.managed_members.filter(is_managed=True).order_by("name")
    managed_pending_requests = WishlistAccessRequest.objects.filter(
        to_user__in=managed_members,
        status="pending",
    ).select_related("from_user", "to_user", "family")

    return render(request, "accounts/dashboard.html", {
        "memberships": memberships,
        "my_items": my_items,
        "pending_requests": pending_requests,
        "item_count": WishlistItem.objects.filter(owner=request.user).count(),
        "item_limit": settings.WISHLIST_ITEM_LIMIT,
        "managed_members": managed_members,
        "managed_pending_requests": managed_pending_requests,
    })


@login_required
def delete_account(request):
    """Confirm and delete the user's account.
    If the user is a guardian, managed members are deleted via CASCADE.
    """
    managed_members = request.user.managed_members.filter(is_managed=True).order_by("name")
    form = DeleteAccountForm(request.POST or None, user=request.user)

    if request.method == "POST" and form.is_valid():
        from django.contrib.auth import logout
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been deleted.")
        return redirect("login")

    return render(request, "accounts/delete_account.html", {
        "form": form,
        "managed_members": managed_members,
    })


@login_required
def create_managed_member(request):
    """Create a managed member (child, elder, etc.) on the guardian's behalf."""
    form = ManagedMemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        import uuid as _uuid
        placeholder_email = f"managed-{_uuid.uuid4().hex}@noreply.internal"
        managed = User(
            email=placeholder_email,
            name=form.cleaned_data["name"],
            is_managed=True,
            guardian=request.user,
            guardian_relationship=form.cleaned_data["relationship"],
            is_email_verified=True,
            is_active=True,
        )
        managed.set_unusable_password()
        managed.save()

        # Auto-join all families the guardian belongs to
        guardian_memberships = FamilyMembership.objects.filter(user=request.user)
        for gm in guardian_memberships:
            FamilyMembership.objects.get_or_create(
                user=managed,
                family=gm.family,
                defaults={"role": "member"},
            )

        # Create notification prefs
        UserNotificationPreference.objects.get_or_create(user=managed)

        messages.success(request, f"{managed.name} has been added as a managed member.")
        return redirect("dashboard")

    return render(request, "accounts/managed_member_form.html", {"form": form})


@login_required
def switch_managed_context(request, member_id):
    """Switch session to manage a specific managed member's wishlist."""
    managed = get_object_or_404(User, pk=member_id, guardian=request.user, is_managed=True)
    request.session["active_managed_member_id"] = str(managed.id)
    messages.info(request, f"Now managing {managed.name}'s wishlist.")
    return redirect(request.GET.get("next", "my_wishlist"))


@login_required
def exit_managed_context(request):
    """Return to managing your own account."""
    request.session.pop("active_managed_member_id", None)
    return redirect(request.GET.get("next", "dashboard"))


@login_required
def preferences(request):
    from django.contrib.auth import update_session_auth_hash

    prefs, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
    family_members = User.objects.filter(
        family_memberships__family__in=request.user.family_memberships.values("family")
    ).exclude(pk=request.user.pk).exclude(is_managed=True).distinct()

    subscriptions = NewItemNotificationSubscription.objects.filter(
        subscriber=request.user
    ).values_list("target_user_id", flat=True)

    password_form = ChangePasswordForm(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "change_password":
            password_form = ChangePasswordForm(request.POST, user=request.user)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data["new_password"])
                request.user.save(update_fields=["password"])
                update_session_auth_hash(request, request.user)
                messages.success(request, "Password updated successfully.")
                return redirect("preferences")

        else:
            prefs.notify_on_access_request = "notify_on_access_request" in request.POST
            prefs.save()
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
        "password_form": password_form,
    })
