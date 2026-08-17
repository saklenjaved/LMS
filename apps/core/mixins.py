from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class NavActiveMixin:
    nav_active = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nav_active"] = self.nav_active
        return context


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().handle_no_permission()


class EmployeeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "employee"

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().handle_no_permission()
