import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "retirement_planner.settings.local")

app = Celery("retirement_planner")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
