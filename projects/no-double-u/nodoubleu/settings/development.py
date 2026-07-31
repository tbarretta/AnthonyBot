from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Use SQLite for easy local dev if you don't want to set up Postgres
# Comment out and use base.py DATABASES to use Postgres
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
