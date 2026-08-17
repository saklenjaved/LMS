from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="list"),
    path("create/", views.CourseCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.CourseUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.CourseDeleteView.as_view(), name="delete"),
    path("<int:pk>/assign/", views.AssignCourseView.as_view(), name="assign"),
    path("assignments/", views.AssignmentHubView.as_view(), name="assignments"),
    path("quiz-results/", views.QuizResultListView.as_view(), name="quiz_results"),
    path("quizzes/", views.QuizManageListView.as_view(), name="quizzes"),
    path("quizzes/<int:pk>/edit/", views.QuizEditView.as_view(), name="quiz_edit"),
    path("enrollments/", views.EnrollmentListView.as_view(), name="enrollments"),
    path("my/", views.MyCourseListView.as_view(), name="my_list"),
    path("my/history/", views.HistoryListView.as_view(), name="history"),
    path("my/<int:pk>/", views.MyCourseDetailView.as_view(), name="my_detail"),
    path("my/<int:pk>/complete/", views.MarkCompleteView.as_view(), name="mark_complete"),
    path("my/<int:pk>/quiz/", views.QuizView.as_view(), name="quiz"),
    path("my/<int:pk>/quiz-review/", views.quiz_review, name="quiz_review"),
    path("my/<int:pk>/certificate/", views.CertificateView.as_view(), name="certificate"),
]
