from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from accounts import views as accounts_views
from core import views as core_views
from courses import views as courses_views

# Everything under /admin/ — the LMS's own admin section (not Django's
# built-in django-admin). Kept in one "admin_panel" namespace so templates
# and views can reverse any admin page consistently, e.g. admin_panel:dashboard,
# admin_panel:employees, admin_panel:course_list, admin_panel:quizzes.
admin_urlpatterns = [
    path("dashboard/", core_views.dashboard, name="dashboard"),
    path("analytics/", core_views.analytics, name="analytics"),
    path("feedback/", core_views.admin_feedback_list, name="feedback"),

    path("employees/", accounts_views.employee_list, name="employees"),
    path("employees/filter/", accounts_views.employee_filter, name="employee_filter"),
    path("employees/<int:pk>/edit/", accounts_views.edit_employee, name="edit_employee"),
    path("employees/<int:pk>/approve/", accounts_views.approve_employee, name="approve_employee"),
    path("employees/<int:pk>/block/", accounts_views.block_employee, name="block_employee"),
    path("employees/<int:pk>/allow-password-reset/", accounts_views.allow_password_reset, name="allow_password_reset"),

    path("courses/", courses_views.CourseListView.as_view(), name="course_list"),
    path("courses/search-suggest/", courses_views.course_search_suggest, name="course_search_suggest"),
    path("courses/create/", courses_views.CourseCreateView.as_view(), name="course_create"),
    path("courses/<int:pk>/view/", courses_views.course_view, name="course_view"),
    path("courses/<int:pk>/edit/", courses_views.CourseUpdateView.as_view(), name="course_edit"),
    path("courses/<int:pk>/delete/", courses_views.CourseDeleteView.as_view(), name="course_delete"),
    path("courses/<int:pk>/assign/", courses_views.AssignCourseView.as_view(), name="course_assign"),
    path("courses/assignments/", courses_views.AssignmentHubView.as_view(), name="assignments"),
    path("courses/quiz-results/", courses_views.QuizResultListView.as_view(), name="quiz_results"),
    path("courses/quiz-results/filter/", courses_views.quiz_result_filter, name="quiz_result_filter"),
    path("courses/enrollments/", courses_views.EnrollmentListView.as_view(), name="enrollments"),
    path("courses/enrollments/filter/", courses_views.enrollment_filter, name="enrollment_filter"),
    path("courses/<int:pk>/quiz/", courses_views.quiz_questions, name="quiz_questions"),
    path("courses/<int:pk>/quiz/view/", courses_views.quiz_view, name="quiz_view"),
    path("courses/<int:pk>/quiz/add/", courses_views.quiz_add, name="quiz_add"),
    path("courses/<int:pk>/quiz/delete/", courses_views.quiz_delete, name="quiz_delete"),
    path("courses/questions/<int:pk>/edit/", courses_views.quiz_edit, name="quiz_edit"),
    path("courses/questions/<int:pk>/delete/", courses_views.quiz_delete_question, name="quiz_delete_question"),

    path("quizzes/", courses_views.QuizManageListView.as_view(), name="quizzes"),
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
