from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from apps.profiles.models import UserProfile
from .forms import InvestmentAccountForm
from .models import InvestmentAccount


@login_required
def account_list(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    accounts = InvestmentAccount.objects.filter(user_profile=profile)
    return render(request, "investments/account_list.html", {
        "accounts": accounts,
        "profile": profile,
    })


@login_required
def account_create(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = InvestmentAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user_profile = profile
            account.save()
            messages.success(request, f"Account '{account.name}' added.")
            if request.headers.get("HX-Request"):
                # Return HTMX partial for account list row
                return render(request, "investments/partials/account_row.html", {"account": account})
            return redirect("investments:list")
    else:
        form = InvestmentAccountForm()
    return render(request, "investments/account_form.html", {"form": form})


@login_required
def account_edit(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    account = get_object_or_404(InvestmentAccount, pk=pk, user_profile=profile)
    if request.method == "POST":
        form = InvestmentAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, "Account updated.")
            return redirect("investments:list")
    else:
        form = InvestmentAccountForm(instance=account)
    return render(request, "investments/account_form.html", {"form": form, "account": account})


@login_required
def account_delete(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    account = get_object_or_404(InvestmentAccount, pk=pk, user_profile=profile)
    if request.method == "POST":
        name = account.name
        account.delete()
        messages.success(request, f"Account '{name}' removed.")
        if request.headers.get("HX-Request"):
            return render(request, "investments/partials/empty.html")
        return redirect("investments:list")
    return render(request, "investments/account_confirm_delete.html", {"account": account})
