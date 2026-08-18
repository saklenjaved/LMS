from django.db.models import Count, Q
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.courses.models import Course, Enrollment


def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/home.html")


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role == "admin":
        enrollments = Enrollment.objects.all()
        context = {
            "nav_active": "dashboard",
            "course_count": Course.objects.count(),
            "employee_count": User.objects.filter(role=User.Role.EMPLOYEE).count(),
            "enrollment_count": enrollments.count(),
            "passed_count": enrollments.filter(status=Enrollment.Status.PASSED).count(),
            "failed_count": enrollments.filter(status=Enrollment.Status.FAILED).count(),
            "recent_enrollments": enrollments.select_related(
                "employee", "course"
            ).order_by("-assigned_at")[:8],
        }
        return render(request, "core/admin_dashboard.html", context)
    enrollments = (
        Enrollment.objects.filter(employee=request.user)
        .select_related("course")
        .order_by("-assigned_at")
    )
    context = {
        "nav_active": "dashboard",
        "current_courses": enrollments.filter(
            status__in=[Enrollment.Status.ASSIGNED, Enrollment.Status.COMPLETED]
        ),
        "history": enrollments.filter(
            status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED]
        ),
        "assigned_count": sum(
            1 for e in enrollments if e.status == Enrollment.Status.ASSIGNED
        ),
        "passed_count": sum(
            1 for e in enrollments if e.status == Enrollment.Status.PASSED
        ),
        "failed_count": sum(
            1 for e in enrollments if e.status == Enrollment.Status.FAILED
        ),
    }
    return render(request, "core/employee_dashboard.html", context)


def reports(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    enrollments = Enrollment.objects.all()
    total_quiz = enrollments.filter(
        status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED]
    ).count()
    passed = enrollments.filter(status=Enrollment.Status.PASSED).count()
    context = {
        "nav_active": "reports",
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
    return render(request, "core/reports.html", context)
