from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('name-it/', include('apps.naming.urls')),
    path('discussion/', include('apps.discussion.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
]
