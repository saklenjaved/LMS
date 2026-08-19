from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.register, name="register"),
    path("mail/<str:action>/<path:token>/", views.mail_action, name="mail_action"),
    path("employees/", views.employee_list, name="employees"),
    path("employees/<int:pk>/approve/", views.approve_employee, name="approve_employee"),
    path("employees/<int:pk>/block/", views.block_employee, name="block_employee"),
]
