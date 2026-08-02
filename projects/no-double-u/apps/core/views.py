import os
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse, Http404
from django.conf import settings
from .forms import HoneypotUserCreationForm


def is_moderator(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Moderators').exists())

def home(request):
    return render(request, 'core/home.html')

def donate(request):
    return render(request, 'core/donate.html')


def the_case(request):
    return render(request, 'core/the_case.html')


def hall_of_fame(request):
    return render(request, 'core/hall_of_fame.html')


def join(request):
    if request.method == 'POST':
        form = HoneypotUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('discussion:discussion')
    else:
        form = HoneypotUserCreationForm()
    return render(request, 'core/join.html', {'form': form})

from apps.discussion.models import Comment
from apps.naming.models import NameSuggestion

@user_passes_test(is_moderator)
def moderation_hub(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        item_id = request.POST.get('item_id')

        if action == 'approve_topic':
            Comment.objects.filter(id=item_id).update(is_approved=True)
        elif action == 'delete_comment':
            Comment.objects.filter(id=item_id).delete()
        elif action == 'unflag_comment':
            Comment.objects.filter(id=item_id).update(is_flagged=False)
        elif action == 'approve_suggestion':
            NameSuggestion.objects.filter(id=item_id).update(is_approved=True)
        elif action == 'delete_suggestion':
            NameSuggestion.objects.filter(id=item_id).delete()

        return redirect('core:moderation_hub')

    pending_topics = Comment.objects.filter(parent=None, is_approved=False).prefetch_related('replies')
    flagged_comments = Comment.objects.filter(is_flagged=True)
    pending_suggestions = NameSuggestion.objects.filter(is_approved=False)

    return render(request, 'core/moderation.html', {
        'pending_topics': pending_topics,
        'flagged_comments': flagged_comments,
        'pending_suggestions': pending_suggestions,
    })

@user_passes_test(is_moderator)
def traffic_stats(request):
    report_path = os.path.join(settings.BASE_DIR, 'reports', 'traffic.html')
    if not os.path.exists(report_path):
        return HttpResponse("Traffic report is currently being generated. Please check back in a few minutes.", status=404)
    with open(report_path, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    return HttpResponse(html)
