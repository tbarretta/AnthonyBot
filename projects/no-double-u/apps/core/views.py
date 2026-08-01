from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import HoneypotUserCreationForm


def home(request):
    return render(request, 'core/home.html')


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

from django.contrib.admin.views.decorators import staff_member_required
from apps.discussion.models import Comment
from apps.naming.models import NameSuggestion

@staff_member_required
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
