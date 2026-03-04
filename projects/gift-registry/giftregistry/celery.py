import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "giftregistry.settings.dev")

app = Celery("giftregistry")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
