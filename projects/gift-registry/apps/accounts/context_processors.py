def active_managed_member(request):
    """
    Injects `active_managed_member` (User or None) into every template context.
    Set when a guardian is managing a member's wishlist via session.
    """
    if not request.user.is_authenticated:
        return {"active_managed_member": None}

    mid = request.session.get("active_managed_member_id")
    if not mid:
        return {"active_managed_member": None}

    from apps.accounts.models import User
    try:
        member = User.objects.get(pk=mid, guardian=request.user, is_managed=True)
        return {"active_managed_member": member}
    except User.DoesNotExist:
        request.session.pop("active_managed_member_id", None)
        return {"active_managed_member": None}


def active_theme(request):
    """
    Injects `active_theme` into every template context.
    Uses the family from the current URL if available,
    otherwise falls back to the user's first family, then 'celebration'.
    """
    if not request.user.is_authenticated:
        return {"active_theme": "celebration"}

    # Check if a family_id is in the URL kwargs (family detail / admin pages)
    family_id = request.resolver_match.kwargs.get("family_id") if request.resolver_match else None
    if family_id:
        from apps.families.models import FamilyMembership
        membership = FamilyMembership.objects.filter(
            user=request.user, family_id=family_id
        ).select_related("family").first()
        if membership:
            return {"active_theme": membership.family.theme}

    # Fall back to first family
    first = request.user.family_memberships.select_related("family").first()
    if first:
        return {"active_theme": first.family.theme}

    return {"active_theme": "celebration"}
