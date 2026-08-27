from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User
from courses.models import Course, Enrollment

from .forms import FeedbackForm
from .models import Feedback


def redirect_localhost(get_response):
    def middleware(request):
        host = request.get_host().split(":")[0]
        if host == "localhost":
            return HttpResponseRedirect(settings.SITE_URL + request.get_full_path())
        return get_response(request)

    return middleware


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
    due_soon_qs = enrollments.filter(
        status=Enrollment.Status.ASSIGNED, completed_at__isnull=True
    ).order_by("due_at")
    next_due_course = due_soon_qs.first()
    upcoming_deadlines = due_soon_qs.exclude(pk=next_due_course.pk) if next_due_course else due_soon_qs
    next_due_overdue = bool(next_due_course and next_due_course.due_at < timezone.now())
    latest_certificate = (
        enrollments.filter(status=Enrollment.Status.PASSED)
        .order_by("-quiz_taken_at")
        .first()
    )

    activity = []
    for e in enrollments:
        activity.append({"date": e.assigned_at, "text": f"Assigned “{e.course.title}”", "icon": "bi-journal-plus"})
        if e.completed_at:
            activity.append({"date": e.completed_at, "text": f"Marked “{e.course.title}” complete", "icon": "bi-check2-circle"})
        if e.quiz_taken_at:
            result = "passed" if e.status == Enrollment.Status.PASSED else "failed"
            activity.append({"date": e.quiz_taken_at, "text": f"Took the quiz for “{e.course.title}” and {result}", "icon": "bi-pencil-square"})
    activity.sort(key=lambda item: item["date"], reverse=True)

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
        "next_due_course": next_due_course,
        "next_due_overdue": next_due_overdue,
        "upcoming_deadlines": upcoming_deadlines[:3],
        "recent_activity": activity[:5],
        "latest_certificate": latest_certificate,
    }
    return render(request, "core/employee_dashboard.html", context)


def _pct(part, total):
    if not total:
        return 0
    return round((part / total) * 100)


def _delta_pct(current, previous):
    if not previous:
        return 100 if current else 0
    return round(((current - previous) / previous) * 100, 1)


def _parse_date(value):
    from datetime import datetime

    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _monthly_counts(queryset, field, months=6):
    now = timezone.now()
    labels = []
    counts = []
    year, month = now.year, now.month
    ranges = []
    for _ in range(months):
        start = timezone.datetime(year, month, 1, tzinfo=now.tzinfo)
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1
        end = timezone.datetime(next_year, next_month, 1, tzinfo=now.tzinfo)
        ranges.append((start, end))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    ranges.reverse()
    for start, end in ranges:
        labels.append(start.strftime("%b"))
        counts.append(
            queryset.filter(**{f"{field}__gte": start, f"{field}__lt": end}).count()
        )
    return labels, counts


def analytics(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employees = User.objects.filter(role=User.Role.EMPLOYEE)
    enrollments = Enrollment.objects.all()

    from_date = _parse_date(request.GET.get("from_date", ""))
    to_date = _parse_date(request.GET.get("to_date", ""))
    ranged_enrollments = enrollments
    if from_date:
        ranged_enrollments = ranged_enrollments.filter(assigned_at__date__gte=from_date)
    if to_date:
        ranged_enrollments = ranged_enrollments.filter(assigned_at__date__lte=to_date)

    pending = employees.filter(status=User.Status.PENDING).count()
    approved = employees.filter(status=User.Status.APPROVED).count()
    blocked = employees.filter(status=User.Status.BLOCKED).count()
    assigned = enrollments.filter(status=Enrollment.Status.ASSIGNED).count()
    completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
    passed = enrollments.filter(status=Enrollment.Status.PASSED).count()
    failed = enrollments.filter(status=Enrollment.Status.FAILED).count()
    total = enrollments.count()
    total_quiz = passed + failed
    week_ago = timezone.now() - timedelta(days=7)
    now = timezone.now()

    active_learners = ranged_enrollments.values("employee_id").distinct().count()
    prev_window_days = 30
    prev_start = now - timedelta(days=prev_window_days * 2)
    prev_end = now - timedelta(days=prev_window_days)
    active_learners_prev = (
        enrollments.filter(assigned_at__gte=prev_start, assigned_at__lt=prev_end)
        .values("employee_id")
        .distinct()
        .count()
    )
    active_learners_recent = (
        enrollments.filter(assigned_at__gte=prev_end)
        .values("employee_id")
        .distinct()
        .count()
    )

    ranged_passed = ranged_enrollments.filter(status=Enrollment.Status.PASSED).count()
    ranged_failed = ranged_enrollments.filter(status=Enrollment.Status.FAILED).count()
    ranged_total_quiz = ranged_passed + ranged_failed
    completion_pct = round((ranged_passed / ranged_total_quiz) * 100, 1) if ranged_total_quiz else 0
    prev_passed = enrollments.filter(
        status=Enrollment.Status.PASSED, quiz_taken_at__gte=prev_start, quiz_taken_at__lt=prev_end
    ).count()
    prev_failed = enrollments.filter(
        status=Enrollment.Status.FAILED, quiz_taken_at__gte=prev_start, quiz_taken_at__lt=prev_end
    ).count()
    prev_total_quiz = prev_passed + prev_failed
    completion_pct_prev = round((prev_passed / prev_total_quiz) * 100, 1) if prev_total_quiz else 0

    overdue_learners = enrollments.filter(
        due_at__lt=now, completed_at__isnull=True
    ).count()
    overdue_learners_prev = enrollments.filter(
        due_at__lt=prev_end, due_at__gte=prev_start, completed_at__isnull=True
    ).count()

    certificates_issued = ranged_passed
    certificates_prev = prev_passed

    quizzes_recent = enrollments.filter(quiz_taken_at__gte=prev_end).count()
    quizzes_prev = enrollments.filter(
        quiz_taken_at__gte=prev_start, quiz_taken_at__lt=prev_end
    ).count()

    active_learners_labels, active_learners_series = _monthly_counts(
        enrollments, "assigned_at"
    )
    completion_labels, completion_series = _monthly_counts(
        enrollments.filter(completed_at__isnull=False), "completed_at"
    )

    emp_buckets = {
        "pending": (employees.filter(status=User.Status.PENDING), "Pending login"),
        "approved": (employees.filter(status=User.Status.APPROVED), "Approved employees"),
        "blocked": (employees.filter(status=User.Status.BLOCKED), "Blocked"),
    }
    emp_kpi = request.GET.get("emp_kpi", "pending")
    if emp_kpi not in emp_buckets:
        emp_kpi = "pending"
    emp_kpi_qs, emp_kpi_title = emp_buckets[emp_kpi]

    enroll_buckets = {
        "assigned": (enrollments.filter(status=Enrollment.Status.ASSIGNED), "Assigned"),
        "completed": (enrollments.filter(status=Enrollment.Status.COMPLETED), "Completed (awaiting quiz)"),
        "passed": (enrollments.filter(status=Enrollment.Status.PASSED), "Passed"),
        "failed": (enrollments.filter(status=Enrollment.Status.FAILED), "Failed"),
    }
    enroll_kpi = request.GET.get("enroll_kpi", "assigned")
    if enroll_kpi not in enroll_buckets:
        enroll_kpi = "assigned"
    enroll_kpi_qs, enroll_kpi_title = enroll_buckets[enroll_kpi]

    context = {
        "nav_active": "analytics",
        "from_date": request.GET.get("from_date", ""),
        "to_date": request.GET.get("to_date", ""),
        "active_learners": active_learners,
        "active_learners_delta": _delta_pct(active_learners_recent, active_learners_prev),
        "active_courses": Course.objects.count(),
        "completion_pct": completion_pct,
        "completion_pct_delta": _delta_pct(completion_pct, completion_pct_prev),
        "certificates_issued": certificates_issued,
        "certificates_delta": _delta_pct(certificates_issued, certificates_prev),
        "overdue_learners": overdue_learners,
        "overdue_learners_delta": _delta_pct(overdue_learners, overdue_learners_prev),
        "quizzes_recent": quizzes_recent,
        "quizzes_recent_delta": _delta_pct(quizzes_recent, quizzes_prev),
        "active_learners_labels": active_learners_labels,
        "active_learners_series": active_learners_series,
        "completion_labels": completion_labels,
        "completion_series": completion_series,
        "pending_count": pending,
        "approved_count": approved,
        "blocked_count": blocked,
        "employee_count": employees.count(),
        "course_count": Course.objects.count(),
        "enrollment_count": total,
        "assigned_count": assigned,
        "completed_count": completed,
        "passed_count": passed,
        "failed_count": failed,
        "pass_rate": round((passed / total_quiz) * 100) if total_quiz else 0,
        "assigned_pct": _pct(assigned, total),
        "completed_pct": _pct(completed, total),
        "passed_pct": _pct(passed, total),
        "failed_pct": _pct(failed, total),
        "assigned_week": enrollments.filter(assigned_at__gte=week_ago).count(),
        "quizzes_week": enrollments.filter(quiz_taken_at__gte=week_ago).count(),
        "emp_kpi": emp_kpi,
        "emp_kpi_title": emp_kpi_title,
        "emp_kpi_rows": emp_kpi_qs.order_by("first_name", "email")[:50],
        "enroll_kpi": enroll_kpi,
        "enroll_kpi_title": enroll_kpi_title,
        "enroll_kpi_rows": enroll_kpi_qs.select_related("employee", "course").order_by(
            "-assigned_at"
        )[:50],
        "top_learners": employees.annotate(
            assigned_count=Count("enrollments"),
            passed_count=Count(
                "enrollments",
                filter=Q(enrollments__status=Enrollment.Status.PASSED),
            ),
        ).order_by("-passed_count", "first_name")[:8],
        "recent_quizzes": enrollments.filter(quiz_taken_at__isnull=False)
        .select_related("employee", "course")
        .order_by("-quiz_taken_at")[:8],
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
    return render(request, "core/analytics.html", context)


def feedback(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "employee":
        return redirect("core:dashboard")
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, "Thanks for your feedback.")
            return redirect("core:feedback")
    else:
        form = FeedbackForm()
    return render(
        request,
        "core/feedback_form.html",
        {
            "nav_active": "feedback",
            "form": form,
            "my_feedback": Feedback.objects.filter(user=request.user),
        },
    )


def admin_feedback_list(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    entries = Feedback.objects.select_related("user")
    paginator = Paginator(entries, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/admin_feedback_list.html",
        {
            "nav_active": "feedback",
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
        },
    )
