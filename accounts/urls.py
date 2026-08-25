from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("register/", views.register, name="register"),
    path("password-reset/", views.password_reset, name="password_reset"),
    path(
        "password-reset/<path:token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path("mail/<str:action>/<path:token>/", views.mail_action, name="mail_action"),
]
