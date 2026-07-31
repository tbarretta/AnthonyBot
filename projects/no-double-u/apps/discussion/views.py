from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
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
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
        Comment.objects.create(
            author_name=request.user.username,
            author_email=request.user.email,
            body=body,
            parent=parent,
        )

    return redirect('discussion:discussion')
