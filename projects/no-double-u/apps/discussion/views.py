from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Comment


def discussion(request):
    comments = Comment.objects.filter(parent=None, is_approved=True).prefetch_related('replies')
    return render(request, 'discussion/discussion.html', {'comments': comments})


@require_POST
def add_comment(request):
    author_name = request.POST.get('author_name', '').strip()
    author_email = request.POST.get('author_email', '').strip()
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')

    if author_name and body:
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
        Comment.objects.create(
            author_name=author_name,
            author_email=author_email,
            body=body,
            parent=parent,
        )

    return redirect('discussion:discussion')
