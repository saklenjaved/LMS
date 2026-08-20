from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import analytics

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("analytics/", analytics, name="analytics"),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("courses/", include("apps.courses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
