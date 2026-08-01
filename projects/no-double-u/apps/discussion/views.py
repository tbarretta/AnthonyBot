from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from apps.core.utils import get_moderator_emails
from .models import Comment


def discussion(request):
    comments = Comment.objects.filter(parent=None, is_approved=True).prefetch_related('replies')
    return render(request, 'discussion/discussion.html', {'comments': comments})


@login_required
@require_POST
def add_comment(request):
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')

    if body:
        parent = None
        is_new_thread = True
        is_approved = False
        
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
            is_new_thread = False
            is_approved = True  # Replies are approved by default
            
        Comment.objects.create(
            author_name=request.user.username,
            author_email=request.user.email,
            body=body,
            parent=parent,
            is_approved=is_approved
        )
        
        if is_new_thread:
            # Notify the moderators via email
            recipient_list = get_moderator_emails()
            if recipient_list:
                try:
                    send_mail(
                        subject='[No Double-U] New Discussion Topic Requires Approval',
                        message=f'A new discussion topic has been posted by {request.user.username} and requires approval.\n\nBody:\n{body}\n\nPlease review it in the moderation queue.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=recipient_list,
                        fail_silently=True,
                    )
                except Exception:
                    pass
                
            messages.success(request, 'Your new topic has been submitted and is pending moderator approval.')
        else:
            messages.success(request, 'Your reply has been posted.')

    return redirect('discussion:discussion')


@login_required
@require_POST
def flag_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    
    if not comment.is_flagged:
        comment.is_flagged = True
        comment.save()
        
    comment.flagged_by.add(request.user)
        
    # Notify the moderators via email
    recipient_list = get_moderator_emails()
    if recipient_list:
        try:
            send_mail(
                subject='[No Double-U] Comment Flagged for Review',
                message=f'A comment by {comment.author_name} was flagged as inappropriate by {request.user.username}.\n\nOriginal Text:\n{comment.body}\n\nPlease review it in the moderation queue.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                fail_silently=True,
            )
        except Exception:
            pass
        
    messages.success(request, 'This comment has been flagged for moderator review.')
        
    return redirect('discussion:discussion')
