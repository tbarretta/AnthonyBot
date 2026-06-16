from django.contrib import admin
from django.urls import path, include
from two_factor.urls import urlpatterns as tf_urls
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(tf_urls)),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("", include("apps.profiles.urls", namespace="profiles")),
    path("investments/", include("apps.investments.urls", namespace="investments")),
    path("simulations/", include("apps.simulations.urls", namespace="simulations")),
    path("api/v1/", include("apps.api.urls", namespace="api")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
