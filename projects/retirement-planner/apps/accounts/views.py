import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from .forms import AccountSettingsForm, InvitationForm, RegisterForm
from .models import Invitation, User
from apps.profiles.forms import UserProfileForm, SpouseProfileForm
from apps.profiles.models import UserProfile, SpouseProfile


def is_admin(user):
    return user.is_staff or user.is_superuser


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Django's default login form uses 'username'; we use email
        form.fields["username"].label = "Email"
        return form


class CustomLogoutView(LogoutView):
    pass


def register(request, token):
    """
    Token-gated registration. Token comes from an Invitation email link.
    """
    try:
        token_uuid = uuid.UUID(str(token))
    except ValueError:
        messages.error(request, "Invalid invitation link.")
        return redirect("accounts:login")

    invitation = get_object_or_404(Invitation, token=token_uuid)

    if not invitation.is_valid:
        messages.error(request, "This invitation has expired or already been used.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = RegisterForm(request.POST, invitation=invitation)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.email  # use email as username
            user.save()

            invitation.used_at = timezone.now()
            invitation.used_by = user
            invitation.save()

            login(request, user)
            messages.success(request, "Welcome! Let's set up your retirement profile.")
            return redirect("profiles:setup")
    else:
        form = RegisterForm(invitation=invitation)

    return render(request, "accounts/register.html", {"form": form, "invitation": invitation})


@login_required
@user_passes_test(is_admin)
def invite_create(request):
    """Master Admin: create and send an invitation."""
    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.created_by = request.user
            invitation.expires_at = timezone.now() + timedelta(days=settings.INVITATION_EXPIRY_DAYS)
            invitation.save()

            # Send invitation email
            register_url = f"{settings.SITE_URL}/accounts/register/{invitation.token}/"
            body = render_to_string("accounts/email/invitation.txt", {
                "register_url": register_url,
                "expiry_days": settings.INVITATION_EXPIRY_DAYS,
            })
            send_mail(
                subject="You've been invited to Retirement Planner",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
            )

            messages.success(request, f"Invitation sent to {invitation.email}.")
            return redirect("accounts:invite_list")
    else:
        form = InvitationForm()

    return render(request, "accounts/invite_form.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def invite_list(request):
    invitations = Invitation.objects.select_related("used_by", "created_by").all()
    return render(request, "accounts/invite_list.html", {"invitations": invitations})


@login_required
def account_settings(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    spouse = SpouseProfile.objects.filter(user_profile=profile).first() if profile else None

    account_form = AccountSettingsForm(instance=request.user)
    profile_form = UserProfileForm(instance=profile) if profile else None
    spouse_form = SpouseProfileForm(instance=spouse)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_account":
            account_form = AccountSettingsForm(request.POST, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                messages.success(request, "Account details updated.")
                return redirect("accounts:settings")

        elif action == "save_profile" and profile:
            profile_form = UserProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated.")
                return redirect("accounts:settings")

        elif action == "save_spouse":
            spouse_form = SpouseProfileForm(request.POST, instance=spouse)
            if spouse_form.is_valid():
                sp = spouse_form.save(commit=False)
                sp.user_profile = profile
                sp.save()
                messages.success(request, "Spouse profile saved.")
                return redirect("accounts:settings")

        elif action == "remove_spouse" and spouse:
            spouse.delete()
            messages.success(request, "Spouse profile removed.")
            return redirect("accounts:settings")

    return render(request, "accounts/account_settings.html", {
        "form": account_form,
        "profile_form": profile_form,
        "spouse_form": spouse_form,
        "profile": profile,
        "spouse": spouse,
    })
