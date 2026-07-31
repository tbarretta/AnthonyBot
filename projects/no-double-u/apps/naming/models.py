from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class NameSuggestion(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    submitted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='suggestions')
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def vote_count(self):
        return self.votes.count()

    def __str__(self):
        return self.name


class Vote(models.Model):
    suggestion = models.ForeignKey(NameSuggestion, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('suggestion', 'user'), ('suggestion', 'session_key')]

    def __str__(self):
        return f"Vote for {self.suggestion}"
