from django.urls import path

from . import views

course_urlpatterns = [
    path("", views.CourseListView.as_view(), name="course_list"),
    path("search-suggest/", views.course_search_suggest, name="course_search_suggest"),
    path("create/", views.CourseCreateView.as_view(), name="course_create"),
    path("<int:pk>/view/", views.course_view, name="course_view"),
    path("<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_edit"),
    path("<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),
    path("<int:pk>/assign/", views.AssignCourseView.as_view(), name="course_assign"),
    path("assignments/", views.AssignmentHubView.as_view(), name="assignments"),
    path("quiz-results/", views.QuizResultListView.as_view(), name="quiz_results"),
    path("quiz-results/filter/", views.quiz_result_filter, name="quiz_result_filter"),
    path("enrollments/", views.EnrollmentListView.as_view(), name="enrollments"),
    path("enrollments/filter/", views.enrollment_filter, name="enrollment_filter"),
    path("<int:pk>/quiz/", views.quiz_questions, name="quiz_questions"),
    path("<int:pk>/quiz/view/", views.quiz_view, name="quiz_view"),
    path("<int:pk>/quiz/add/", views.quiz_add, name="quiz_add"),
    path("<int:pk>/quiz/delete/", views.quiz_delete, name="quiz_delete"),
    path("questions/<int:pk>/edit/", views.quiz_edit, name="quiz_edit"),
    path("questions/<int:pk>/delete/", views.quiz_delete_question, name="quiz_delete_question"),
]

quiz_urlpatterns = [
    path("", views.QuizManageListView.as_view(), name="quizzes"),
]
