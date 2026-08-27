from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("my-courses/", views.MyCourseListView.as_view(), name="my_list"),
    path("my-courses/history/", views.HistoryListView.as_view(), name="history"),
    path("my-courses/<int:pk>/", views.MyCourseDetailView.as_view(), name="my_detail"),
    path("my-courses/<int:pk>/complete/", views.MarkCompleteView.as_view(), name="mark_complete"),
    path("my-courses/<int:pk>/rate/", views.RateCourseView.as_view(), name="rate"),
    path("my-courses/<int:pk>/quiz/", views.QuizView.as_view(), name="quiz"),
    path("my-courses/<int:pk>/quiz-review/", views.quiz_review, name="quiz_review"),
    path("my-courses/<int:pk>/certificate/", views.certificate, name="certificate"),
    path("my-courses/<int:pk>/certificate.pdf/", views.certificate_pdf, name="certificate_pdf"),
]
