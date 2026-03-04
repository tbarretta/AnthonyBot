from .base import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = ["127.0.0.1"]

# In dev, print emails to console instead of sending via SendGrid
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Easier password for dev only
AUTH_PASSWORD_VALIDATORS = []
