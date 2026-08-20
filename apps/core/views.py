from datetime import timedelta

from django.db.models import Count, F, Q
from django.shortcuts import redirect, render
from django.utils import timezone

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
        now = timezone.now()
        soon = now + timedelta(days=7)
        on_time = enrollments.filter(
            completed_at__isnull=False,
            completed_at__lte=F("due_at"),
        )
        late = enrollments.filter(
            completed_at__isnull=False,
            completed_at__gt=F("due_at"),
        )
        overdue = enrollments.filter(
            due_at__lt=now,
            completed_at__isnull=True,
        )
        due_soon = enrollments.filter(
            due_at__gte=now,
            due_at__lte=soon,
            completed_at__isnull=True,
        )
        kpi = request.GET.get("kpi", "overdue")
        buckets = {
            "on_time": (on_time, "Completed on time"),
            "late": (late, "Completed late"),
            "overdue": (overdue, "Overdue (not completed)"),
            "due_soon": (due_soon, "Due in next 7 days"),
        }
        if kpi not in buckets:
            kpi = "overdue"
        kpi_qs, kpi_title = buckets[kpi]
        context = {
            "nav_active": "dashboard",
            "kpi": kpi,
            "kpi_title": kpi_title,
            "on_time_employees": on_time.values("employee").distinct().count(),
            "on_time_assignments": on_time.count(),
            "late_employees": late.values("employee").distinct().count(),
            "late_assignments": late.count(),
            "overdue_employees": overdue.values("employee").distinct().count(),
            "overdue_assignments": overdue.count(),
            "due_soon_employees": due_soon.values("employee").distinct().count(),
            "due_soon_assignments": due_soon.count(),
            "kpi_rows": kpi_qs.select_related("employee", "course").order_by("due_at"),
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


def _pct(part, total):
    if not total:
        return 0
    return round((part / total) * 100)


def analytics(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employees = User.objects.filter(role=User.Role.EMPLOYEE)
    enrollments = Enrollment.objects.all()
    pending = employees.filter(status=User.Status.PENDING).count()
    approved = employees.filter(status=User.Status.APPROVED).count()
    blocked = employees.filter(status=User.Status.BLOCKED).count()
    assigned = enrollments.filter(status=Enrollment.Status.ASSIGNED).count()
    completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
    passed = enrollments.filter(status=Enrollment.Status.PASSED).count()
    failed = enrollments.filter(status=Enrollment.Status.FAILED).count()
    total = enrollments.count()
    week_ago = timezone.now() - timedelta(days=7)
    context = {
        "nav_active": "analytics",
        "pending_count": pending,
        "approved_count": approved,
        "blocked_count": blocked,
        "assigned_count": assigned,
        "completed_count": completed,
        "passed_count": passed,
        "failed_count": failed,
        "assigned_pct": _pct(assigned, total),
        "completed_pct": _pct(completed, total),
        "passed_pct": _pct(passed, total),
        "failed_pct": _pct(failed, total),
        "assigned_week": enrollments.filter(assigned_at__gte=week_ago).count(),
        "quizzes_week": enrollments.filter(quiz_taken_at__gte=week_ago).count(),
        "top_learners": employees.annotate(
            passed_count=Count(
                "enrollments",
                filter=Q(enrollments__status=Enrollment.Status.PASSED),
            )
        ).order_by("-passed_count", "first_name")[:8],
        "recent_quizzes": enrollments.filter(quiz_taken_at__isnull=False)
        .select_related("employee", "course")
        .order_by("-quiz_taken_at")[:8],
    }
    return render(request, "core/analytics.html", context)
