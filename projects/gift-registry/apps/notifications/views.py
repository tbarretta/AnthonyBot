from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from .models import ActivityLog


def master_admin_required(view_func):
    """Decorator: only master admins can access."""
    from functools import wraps
    from django.http import Http404

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_master_admin:
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@master_admin_required
def master_admin(request):
    from django.contrib.auth import get_user_model
    from apps.families.models import Family
    from apps.wishlist.models import WishlistItem

    User = get_user_model()

    # Stats
    stats = {
        "users": User.objects.count(),
        "families": Family.objects.count(),
        "items": WishlistItem.objects.count(),
    }

    # Activity log with filters
    log_qs = ActivityLog.objects.select_related("actor", "target_user", "family")
    event_filter = request.GET.get("event_type", "")
    if event_filter:
        log_qs = log_qs.filter(event_type=event_filter)
    paginator = Paginator(log_qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    # Families
    families = Family.objects.prefetch_related("memberships__user").all()

    # Users
    user_query = request.GET.get("q", "")
    users = User.objects.all()
    if user_query:
        users = users.filter(email__icontains=user_query) | users.filter(name__icontains=user_query)
    users = users.order_by("name")

    from .models import EVENT_TYPES
    return render(request, "admin/master_admin.html", {
        "stats": stats,
        "log_page": page,
        "families": families,
        "users": users,
        "event_types": EVENT_TYPES,
        "event_filter": event_filter,
        "user_query": user_query,
    })


@login_required
@master_admin_required
def delete_family(request, family_id):
    """Master Admin deletes a family. Users are never auto-deleted."""
    from apps.families.models import Family, FamilyMembership
    from django.contrib.auth import get_user_model
    User = get_user_model()

    family = get_object_or_404(Family, pk=family_id)

    # Find members who will lose their only family
    members = User.objects.filter(family_memberships__family=family)
    orphaned = [
        u for u in members
        if u.family_memberships.exclude(family=family).count() == 0
    ]

    if request.method == "POST":
        confirmed = request.POST.get("confirmed")
        if not confirmed:
            messages.error(request, "Please confirm the deletion.")
            return redirect("master_admin")

        family_name = family.name
        family.delete()  # Cascades: memberships, invitations, access requests, item visibility

        ActivityLog.log(
            event_type="family_deleted",
            actor=request.user,
            description=f'Master Admin deleted family "{family_name}"',
        )
        messages.success(request, f'Family "{family_name}" has been deleted.')
        return redirect("master_admin")

    # GET — show confirmation page
    return render(request, "admin/delete_family_confirm.html", {
        "family": family,
        "orphaned_users": orphaned,
    })


@login_required
@master_admin_required
def admin_reset_password(request):
    """Manually trigger a password reset for any user."""
    if request.method == "POST":
        from django.contrib.auth import get_user_model
        from apps.notifications.tasks import send_password_reset_email
        User = get_user_model()
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email=email).first()
        if user:
            send_password_reset_email.delay(str(user.pk))
            ActivityLog.log(
                event_type="admin_pw_reset",
                actor=request.user,
                target_user=user,
                description=f"Master admin triggered password reset for {user.email}",
            )
            messages.success(request, f"Password reset email sent to {email}.")
        else:
            messages.error(request, f"No account found for {email}.")
    return redirect("master_admin")


@login_required
@master_admin_required
def create_family(request):
    """Master Admin creates a new family and invites the first Family Admin."""
    if request.method == "POST":
        from apps.families.models import Family, FamilyInvitation
        from apps.notifications.tasks import send_invitation_email

        family_name = request.POST.get("family_name", "").strip()
        admin_email = request.POST.get("admin_email", "").strip().lower()

        if not family_name or not admin_email:
            messages.error(request, "Family name and admin email are both required.")
            return redirect("master_admin")

        if Family.objects.filter(name__iexact=family_name).exists():
            messages.error(request, f'A family named "{family_name}" already exists.')
            return redirect("master_admin")

        # Create the family (Master Admin as creator)
        family = Family.objects.create(name=family_name, created_by=request.user)

        # If the invited person already has an account, make them admin immediately
        from django.contrib.auth import get_user_model
        User = get_user_model()
        existing_user = User.objects.filter(email=admin_email).first()
        if existing_user:
            from apps.families.models import FamilyMembership
            FamilyMembership.objects.get_or_create(
                user=existing_user, family=family,
                defaults={"role": "admin"}
            )
            ActivityLog.log(
                event_type="family_created",
                actor=request.user,
                family=family,
                description=f'Master Admin created family "{family_name}" and added existing user {admin_email} as Family Admin',
            )
            messages.success(request, f'Family "{family_name}" created. {existing_user.name} has been added as Family Admin.')
        else:
            # Send an invitation with admin role
            inv = FamilyInvitation.objects.create(
                family=family,
                invited_by=request.user,
                email=admin_email,
                role="admin",
            )
            send_invitation_email.delay(str(inv.id))
            ActivityLog.log(
                event_type="family_created",
                actor=request.user,
                family=family,
                description=f'Master Admin created family "{family_name}" and invited {admin_email} as Family Admin',
            )
            messages.success(request, f'Family "{family_name}" created. An invitation has been sent to {admin_email}.')

    return redirect("master_admin")


@login_required
@master_admin_required
def admin_reset_access(request, access_id):
    """Reset a denied access request so the member can re-request."""
    from apps.access.models import WishlistAccessRequest
    req = get_object_or_404(WishlistAccessRequest, pk=access_id, status="denied")
    req.reset()
    ActivityLog.log(
        event_type="access_reset",
        actor=request.user,
        target_user=req.from_user,
        family=req.family,
        description=f"Master admin reset denied access: {req.from_user.name} → {req.to_user.name}",
    )
    messages.success(request, "Access request reset. The member can now re-request.")
    return redirect("master_admin")
