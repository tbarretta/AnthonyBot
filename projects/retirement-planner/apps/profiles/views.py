from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from apps.investments.models import InvestmentAccount
from apps.simulations.models import Scenario
from .forms import UserProfileForm, SpouseProfileForm
from .models import UserProfile, SpouseProfile


@login_required
def dashboard(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    accounts = InvestmentAccount.objects.filter(user_profile=profile)
    scenarios = Scenario.objects.filter(user_profile=profile).order_by("-updated_at")

    total_balance = sum(a.current_balance for a in accounts)
    annual_contributions = sum(a.annual_contribution for a in accounts)

    return render(request, "profiles/dashboard.html", {
        "profile": profile,
        "accounts": accounts,
        "scenarios": scenarios,
        "total_balance": total_balance,
        "annual_contributions": annual_contributions,
    })


@login_required
def profile_setup(request):
    """Initial setup wizard step 1: primary profile."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = None

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.save()
            messages.success(request, "Profile saved.")
            return redirect("profiles:spouse_setup")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "profiles/profile_form.html", {"form": form, "step": 1})


@login_required
def spouse_setup(request):
    """Setup step 2: optional spouse data."""
    profile = get_object_or_404(UserProfile, user=request.user)

    try:
        spouse = profile.spouse
    except SpouseProfile.DoesNotExist:
        spouse = None

    if request.method == "POST":
        if "skip" in request.POST:
            profile.is_setup_complete = True
            profile.save()
            return redirect("profiles:dashboard")

        form = SpouseProfileForm(request.POST, instance=spouse)
        if form.is_valid():
            sp = form.save(commit=False)
            sp.user_profile = profile
            sp.save()
            profile.is_setup_complete = True
            profile.save()
            messages.success(request, "Profile setup complete! Add Social Security estimates when creating a scenario.")
            return redirect("profiles:dashboard")
    else:
        form = SpouseProfileForm(instance=spouse)

    return render(request, "profiles/spouse_form.html", {"form": form, "step": 2})


@login_required
def profile_edit(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profiles:dashboard")
    else:
        form = UserProfileForm(instance=profile)
    return render(request, "profiles/profile_form.html", {"form": form})
