from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from apps.profiles.models import UserProfile
from .forms import InvestmentAccountForm, IncomeSourceForm
from .models import InvestmentAccount, IncomeSource


# ---------------------------------------------------------------------------
# Investment Account CRUD
# ---------------------------------------------------------------------------

@login_required
def account_list(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    accounts = InvestmentAccount.objects.filter(user_profile=profile)
    total_balance = sum(a.current_balance for a in accounts)
    total_contributions = sum(a.annual_contribution for a in accounts)
    return render(request, "investments/account_list.html", {
        "accounts": accounts,
        "total_balance": total_balance,
        "total_contributions": total_contributions,
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


# ---------------------------------------------------------------------------
# Income Source CRUD
# ---------------------------------------------------------------------------

@login_required
def income_source_list(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    income_sources = IncomeSource.objects.filter(user_profile=profile)
    return render(request, "investments/income_source_list.html", {
        "income_sources": income_sources,
        "profile": profile,
    })


@login_required
def income_source_create(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == "POST":
        form = IncomeSourceForm(request.POST)
        if form.is_valid():
            src = form.save(commit=False)
            src.user_profile = profile
            src.save()
            messages.success(request, f"Income source '{src.name}' added.")
            return redirect("investments:income_list")
    else:
        form = IncomeSourceForm()
    return render(request, "investments/income_source_form.html", {
        "form": form,
        "title": "Add Income Source",
    })


@login_required
def income_source_edit(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    src = get_object_or_404(IncomeSource, pk=pk, user_profile=profile)
    if request.method == "POST":
        form = IncomeSourceForm(request.POST, instance=src)
        if form.is_valid():
            form.save()
            messages.success(request, f"Income source '{src.name}' updated.")
            return redirect("investments:income_list")
    else:
        form = IncomeSourceForm(instance=src)
    return render(request, "investments/income_source_form.html", {
        "form": form,
        "income_source": src,
        "title": f"Edit — {src.name}",
    })


@login_required
def income_source_delete(request, pk):
    profile = get_object_or_404(UserProfile, user=request.user)
    src = get_object_or_404(IncomeSource, pk=pk, user_profile=profile)
    if request.method == "POST":
        name = src.name
        src.delete()
        messages.success(request, f"Income source '{name}' removed.")
        return redirect("investments:income_list")
    return render(request, "investments/income_source_confirm_delete.html", {
        "income_source": src,
    })
