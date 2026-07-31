from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm


def home(request):
    return render(request, 'core/home.html')


def the_case(request):
    return render(request, 'core/the_case.html')


def hall_of_fame(request):
    return render(request, 'core/hall_of_fame.html')


def join(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('discussion:discussion')
    else:
        form = UserCreationForm()
    return render(request, 'core/join.html', {'form': form})
