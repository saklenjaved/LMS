from django.urls import path

from . import views

app_name = "communication"

urlpatterns = [
    path("", views.conversation_list, name="list"),
    path("start/", views.conversation_create, name="create"),
    path("<int:pk>/", views.conversation_detail, name="detail"),
]
