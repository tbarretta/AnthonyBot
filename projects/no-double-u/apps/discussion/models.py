from django.db import models


class Comment(models.Model):
    author_name = models.CharField(max_length=100)
    author_email = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author_name}: {self.body[:50]}"
