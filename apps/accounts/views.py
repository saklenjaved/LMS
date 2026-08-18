from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db.models import Count
from django.shortcuts import redirect, render

from .forms import EmailAuthenticationForm, RegisterForm
from .models import User


def login(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("core:dashboard")
    else:
        form = EmailAuthenticationForm(request)
    return render(request, "accounts/login.html", {"form": form})


def logout(request):
    if request.method == "POST":
        auth_logout(request)
    return redirect("accounts:login")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("accounts:login")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def employee_list(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employees = (
        User.objects.filter(role=User.Role.EMPLOYEE)
        .annotate(course_count=Count("enrollments"))
        .order_by("first_name", "email")
    )
    return render(
        request,
        "accounts/employee_list.html",
        {"employees": employees, "nav_active": "employees"},
    )
