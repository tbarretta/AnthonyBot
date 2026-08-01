from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from .models import NameSuggestion, Vote


def name_it(request):
    suggestions = NameSuggestion.objects.filter(is_approved=True)
    # Sort by vote count in Python since it's a property
    suggestions = sorted(suggestions, key=lambda s: s.vote_count, reverse=True)

    # Track which suggestions the current user/session has voted for
    voted_ids = set()
    if request.user.is_authenticated:
        voted_ids = set(Vote.objects.filter(user=request.user).values_list('suggestion_id', flat=True))
    elif request.session.session_key:
        voted_ids = set(Vote.objects.filter(session_key=request.session.session_key).values_list('suggestion_id', flat=True))

    return render(request, 'naming/name_it.html', {
        'suggestions': suggestions,
        'voted_ids': voted_ids,
    })


@require_POST
def vote(request, pk):
    suggestion = get_object_or_404(NameSuggestion, pk=pk, is_approved=True)

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    try:
        if request.user.is_authenticated:
            Vote.objects.create(suggestion=suggestion, user=request.user)
        else:
            Vote.objects.create(suggestion=suggestion, session_key=request.session.session_key)
        voted = True
    except IntegrityError:
        voted = True  # already voted

    return JsonResponse({'votes': suggestion.vote_count, 'voted': voted})


@require_POST
def suggest(request):
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if name:
        suggestion = NameSuggestion.objects.create(
            name=name,
            description=description,
            submitted_by=request.user if request.user.is_authenticated else None,
            is_approved=False,
        )
        
        # Notify the admin via email
        try:
            submitter_name = request.user.username if request.user.is_authenticated else "An anonymous user"
            send_mail(
                subject=f'[No Double-U] New Name Suggestion: {name}',
                message=f'A new name suggestion has been submitted.\n\nName: {name}\nDescription: {description}\nSubmitted by: {submitter_name}\n\nReview it in the admin dashboard.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=True,
            )
        except Exception:
            pass
            
        messages.success(request, f'Thanks! "{name}" has been submitted for review.')
    else:
        messages.error(request, 'Please enter a name.')

    return redirect('naming:name_it')
