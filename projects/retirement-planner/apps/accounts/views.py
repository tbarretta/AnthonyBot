import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import (
    LoginView, LogoutView,
    PasswordResetView, PasswordResetConfirmView, PasswordChangeView,
)
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from two_factor.utils import default_device

from .forms import AccountSettingsForm, InvitationForm, RegisterForm
from .models import Invitation, User, AuditLog, AuditEvent
from apps.profiles.forms import UserProfileForm, SpouseProfileForm
from apps.profiles.models import UserProfile, SpouseProfile


def is_admin(user):
    return user.is_staff or user.is_superuser


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Django's default login form uses 'username'; we use email
        form.fields["username"].label = "Email"
        return form


class CustomLogoutView(LogoutView):
    pass


# ---------------------------------------------------------------------------
# Custom password views with audit logging
# ---------------------------------------------------------------------------

class CustomPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/email/password_reset.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    success_url = "/accounts/password/reset/done/"

    def form_valid(self, form):
        email = form.cleaned_data.get('email', '')
        user_qs = User.objects.filter(email=email)
        user = user_qs.first() if user_qs.exists() else None
        AuditLog.objects.create(
            user=user,
            user_email=email,
            event=AuditEvent.PASSWORD_RESET_REQUEST,
            ip_address=_get_ip(self.request),
        )
        return super().form_valid(form)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = "/accounts/password/reset/complete/"

    def form_valid(self, form):
        user = form.user
        AuditLog.objects.create(
            user=user,
            user_email=user.email if user else '',
            event=AuditEvent.PASSWORD_RESET_COMPLETE,
            ip_address=_get_ip(self.request),
        )
        return super().form_valid(form)


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = "/accounts/password/change/done/"

    def form_valid(self, form):
        user = self.request.user
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            event=AuditEvent.PASSWORD_CHANGED,
            ip_address=_get_ip(self.request),
        )
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

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

            # Audit: user created + invitation used
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                event=AuditEvent.USER_CREATED,
                ip_address=_get_ip(request),
            )
            AuditLog.objects.create(
                user=user,
                user_email=user.email,
                event=AuditEvent.INVITATION_USED,
                ip_address=_get_ip(request),
                notes=f"Invitation token: {invitation.token}",
            )

            login(request, user)
            messages.success(request, "Welcome! Let's set up your retirement profile.")
            return redirect("profiles:setup")
    else:
        form = RegisterForm(invitation=invitation)

    return render(request, "accounts/register.html", {"form": form, "invitation": invitation})


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------

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

            # Audit
            AuditLog.objects.create(
                actor=request.user,
                user_email=invitation.email,
                event=AuditEvent.INVITATION_CREATED,
                ip_address=_get_ip(request),
                notes=f"Invitation token: {invitation.token}",
            )

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
@user_passes_test(is_admin)
def invite_delete(request, pk):
    invitation = get_object_or_404(Invitation, pk=pk)
    if request.method == "POST":
        email = invitation.email
        invitation.delete()
        messages.success(request, f"Invitation for {email} has been removed.")
        return redirect("accounts:invite_list")
    
    return render(request, "accounts/invite_confirm_delete.html", {"invitation": invitation})


# ---------------------------------------------------------------------------
# Account settings
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    from django.utils import timezone as tz
    from datetime import timedelta as td
    recent = AuditLog.objects.select_related('user', 'actor').all()[:10]
    user_count = User.objects.count()
    last_24h = tz.now() - td(hours=24)
    recent_event_count = AuditLog.objects.filter(timestamp__gte=last_24h).count()
    pending_invitations = Invitation.objects.filter(used_at__isnull=True, expires_at__gt=tz.now()).count()
    return render(request, 'accounts/admin/dashboard.html', {
        'recent': recent,
        'user_count': user_count,
        'recent_event_count': recent_event_count,
        'pending_invitations': pending_invitations,
    })


@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    users = User.objects.all().order_by('-date_joined').select_related('invitation')
    for u in users:
        u.has_mfa = default_device(u) is not None
    return render(request, 'accounts/admin/user_list.html', {'users': users})


@login_required
@user_passes_test(is_admin)
def admin_user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('accounts:admin_user_list')
    if request.method == 'POST':
        email = target.email
        AuditLog.objects.create(
            actor=request.user,
            user_email=email,
            event=AuditEvent.USER_DELETED,
            ip_address=_get_ip(request),
            notes=f"Deleted by {request.user.email}",
        )
        target.delete()
        messages.success(request, f"User {email} deleted.")
        return redirect('accounts:admin_user_list')
    return render(request, 'accounts/admin/user_delete.html', {'target': target})


@login_required
@user_passes_test(is_admin)
def admin_user_reset_password(request, pk):
    from django.contrib.auth.forms import PasswordResetForm
    target = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = PasswordResetForm({'email': target.email})
        if form.is_valid():
            form.save(
                request=request,
                email_template_name='accounts/email/password_reset.txt',
                subject_template_name='accounts/email/password_reset_subject.txt',
            )
        AuditLog.objects.create(
            actor=request.user,
            user=target,
            user_email=target.email,
            event=AuditEvent.ADMIN_PASSWORD_RESET,
            ip_address=_get_ip(request),
            notes=f"Reset triggered by {request.user.email}",
        )
        messages.success(request, f"Password reset email sent to {target.email}.")
        return redirect('accounts:admin_user_list')
    return render(request, 'accounts/admin/user_reset_password.html', {'target': target})


@login_required
@user_passes_test(is_admin)
def admin_audit_log(request):
    from django.core.paginator import Paginator
    logs = AuditLog.objects.select_related('user', 'actor').all()
    event_filter = request.GET.get('event', '')
    user_filter = request.GET.get('user', '')
    if event_filter:
        logs = logs.filter(event=event_filter)
    if user_filter:
        logs = logs.filter(user_email__icontains=user_filter)
    paginator = Paginator(logs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/admin/audit_log.html', {
        'page': page,
        'event_filter': event_filter,
        'user_filter': user_filter,
        'event_choices': AuditEvent.choices,
    })
