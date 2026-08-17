from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.core.mixins import AdminRequiredMixin, NavActiveMixin
from apps.courses.models import Course, Enrollment


class DashboardView(LoginRequiredMixin, NavActiveMixin, TemplateView):
    nav_active = "dashboard"

    def get_template_names(self):
        if self.request.user.role == "admin":
            return ["core/admin_dashboard.html"]
        return ["core/employee_dashboard.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.role == "admin":
            enrollments = Enrollment.objects.all()
            context["course_count"] = Course.objects.count()
            context["employee_count"] = User.objects.filter(role=User.Role.EMPLOYEE).count()
            context["enrollment_count"] = enrollments.count()
            context["passed_count"] = enrollments.filter(status=Enrollment.Status.PASSED).count()
            context["failed_count"] = enrollments.filter(status=Enrollment.Status.FAILED).count()
            context["recent_enrollments"] = enrollments.select_related(
                "employee", "course"
            ).order_by("-assigned_at")[:8]
        else:
            enrollments = (
                Enrollment.objects.filter(employee=user)
                .select_related("course")
                .order_by("-assigned_at")
            )
            current = enrollments.filter(
                status__in=[Enrollment.Status.ASSIGNED, Enrollment.Status.COMPLETED]
            )
            history = enrollments.filter(
                status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED]
            )
            context["current_courses"] = current
            context["history"] = history
            context["assigned_count"] = sum(
                1 for e in enrollments if e.status == Enrollment.Status.ASSIGNED
            )
            context["passed_count"] = sum(
                1 for e in enrollments if e.status == Enrollment.Status.PASSED
            )
            context["failed_count"] = sum(
                1 for e in enrollments if e.status == Enrollment.Status.FAILED
            )
        return context


class ReportsView(NavActiveMixin, AdminRequiredMixin, TemplateView):
    template_name = "core/reports.html"
    nav_active = "reports"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = Enrollment.objects.all()
        total_quiz = enrollments.filter(
            status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED]
        ).count()
        passed = enrollments.filter(status=Enrollment.Status.PASSED).count()
        context.update(
            {
                "employee_count": User.objects.filter(role=User.Role.EMPLOYEE).count(),
                "course_count": Course.objects.count(),
                "enrollment_count": enrollments.count(),
                "assigned_count": enrollments.filter(status=Enrollment.Status.ASSIGNED).count(),
                "completed_count": enrollments.filter(status=Enrollment.Status.COMPLETED).count(),
                "passed_count": passed,
                "failed_count": enrollments.filter(status=Enrollment.Status.FAILED).count(),
                "pass_rate": round((passed / total_quiz) * 100) if total_quiz else 0,
                "course_stats": Course.objects.annotate(
                    assigned=Count("enrollments"),
                    passed=Count(
                        "enrollments",
                        filter=Q(enrollments__status=Enrollment.Status.PASSED),
                    ),
                    failed=Count(
                        "enrollments",
                        filter=Q(enrollments__status=Enrollment.Status.FAILED),
                    ),
                ).order_by("title"),
            }
        )
        return context


class HomeView(TemplateView):
    template_name = "core/home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)
