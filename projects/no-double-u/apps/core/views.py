from django.shortcuts import render


def home(request):
    return render(request, 'core/home.html')


def the_case(request):
    return render(request, 'core/the_case.html')


def hall_of_fame(request):
    return render(request, 'core/hall_of_fame.html')
