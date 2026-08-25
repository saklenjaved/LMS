from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from courses.admin_urls import course_urlpatterns, quiz_urlpatterns

# Everything under /admin/ — the LMS's own admin section (not Django's
# built-in django-admin). Kept in one "admin_panel" namespace so templates
# and views can reverse any admin page consistently, e.g. admin_panel:dashboard,
# admin_panel:employees, admin_panel:course_list, admin_panel:quizzes.
admin_urlpatterns = [
    path("", include("core.admin_urls")),
    path("employees/", include("accounts.admin_urls")),
    path("courses/", include(course_urlpatterns)),
    path("quizzes/", include(quiz_urlpatterns)),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include((admin_urlpatterns, "admin_panel"), namespace="admin_panel")),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("courses/", include("courses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
