from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("families/", include("apps.families.urls")),
    path("wishlist/", include("apps.wishlist.urls")),
    path("access/", include("apps.access.urls")),
    path("admin/", include("apps.notifications.urls_admin")),
    path("", include("apps.accounts.urls_root")),  # dashboard, home
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
