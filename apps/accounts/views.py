from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.core.mixins import AdminRequiredMixin, NavActiveMixin

from .forms import EmailAuthenticationForm, RegisterForm
from .models import User


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = EmailAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class RegisterView(CreateView):
    model = User
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")


class EmployeeListView(NavActiveMixin, AdminRequiredMixin, ListView):
    template_name = "accounts/employee_list.html"
    context_object_name = "employees"
    nav_active = "employees"

    def get_queryset(self):
        return (
            User.objects.filter(role=User.Role.EMPLOYEE)
            .annotate(course_count=Count("enrollments"))
            .order_by("first_name", "email")
        )
