from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.core.paginator import Paginator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .emails import (
    MAIL_SALT,
    MAIL_SEP,
    RESET_SALT,
    notify_admin_new_employee,
    notify_employee_approved,
    notify_employee_blocked,
    notify_password_reset,
)
from .forms import (
    EmailAuthenticationForm,
    EmployeeUpdateForm,
    NewPasswordForm,
    PasswordResetForm,
    RegisterForm,
)
from .models import User


def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return ""


def _mail_page(request, ok, text):
    return render(request, "accounts/mail_result.html", {"ok": ok, "text": text})


def login(request):
    nxt = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(nxt or "core:dashboard")
    if request.method == "GET":
        form = EmailAuthenticationForm(request)
        return render(request, "accounts/login.html", {"form": form, "next": nxt})
    form = EmailAuthenticationForm(request, data=request.POST)
    if not form.is_valid():
        return render(request, "accounts/login.html", {"form": form, "next": nxt})
    user = form.get_user()
    if user.role == User.Role.EMPLOYEE and user.status == User.Status.PENDING:
        messages.error(
            request,
            "You are not approved by the admin yet. Once the admin approves your account, you can log in.",
        )
        return render(request, "accounts/login.html", {"form": form, "next": nxt})
    if user.role == User.Role.EMPLOYEE and user.status == User.Status.BLOCKED:
        messages.error(
            request,
            "Your account has been blocked by the admin. You cannot log in.",
        )
        return render(request, "accounts/login.html", {"form": form, "next": nxt})
    auth_login(request, user)
    return redirect(nxt or "core:dashboard")


def logout(request):
    if request.method == "POST":
        auth_logout(request)
    return redirect("accounts:login")


def register(request):
    if request.method == "GET":
        return render(request, "accounts/register.html", {"form": RegisterForm()})
    form = RegisterForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/register.html", {"form": form})
    employee = form.save()
    sent = notify_admin_new_employee(employee)
    if sent:
        messages.success(
            request,
            "Account created. Wait for admin approval before you log in.",
        )
    else:
        messages.warning(
            request,
            "Account created, but the admin email could not be sent. "
            "Check SMTP settings in .env, then restart the server.",
        )
    return redirect("accounts:login")


def password_reset(request):
    if request.method == "GET":
        return render(request, "accounts/password_reset.html", {"form": PasswordResetForm()})
    form = PasswordResetForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/password_reset.html", {"form": form})
    email = form.cleaned_data["email"]
    user = User.objects.filter(email__iexact=email).first()
    if user:
        notify_password_reset(user)
    messages.success(
        request,
        "If that email is registered, we sent a reset link.",
    )
    return redirect("accounts:login")


def password_reset_confirm(request, token):
    token = token.rstrip("/")
    try:
        payload = TimestampSigner(salt=RESET_SALT, sep=MAIL_SEP).unsign(
            token, max_age=60 * 60 * 24
        )
        pk, password_hash = payload.split(MAIL_SEP, 1)
    except (BadSignature, SignatureExpired, ValueError):
        messages.error(request, "This reset link is invalid or has expired.")
        return redirect("accounts:password_reset")
    user = User.objects.filter(pk=pk).first()
    if user is None or user.password != password_hash:
        messages.error(request, "This reset link is invalid or has expired.")
        return redirect("accounts:password_reset")
    if request.method == "GET":
        return render(
            request,
            "accounts/password_reset_confirm.html",
            {"form": NewPasswordForm()},
        )
    form = NewPasswordForm(request.POST)
    if not form.is_valid():
        return render(request, "accounts/password_reset_confirm.html", {"form": form})
    user.set_password(form.cleaned_data["password1"])
    user.save()
    messages.success(request, "Password updated. You can log in now.")
    return redirect("accounts:login")


EMPLOYEE_SORT_OPTIONS = {
    "registered_asc": ("date_joined",),
    "registered_desc": ("-date_joined",),
    "name_asc": ("first_name", "email"),
    "name_desc": ("-first_name", "-email"),
    "status": ("status", "first_name", "email"),
}
DEFAULT_EMPLOYEE_SORT = "registered_desc"


def filter_employees(queryset, params):
    q = params.get("q", "").strip()
    status = params.get("status", "").strip()
    sort = params.get("sort", "").strip()

    if q:
        queryset = queryset.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    if status in (User.Status.PENDING, User.Status.APPROVED, User.Status.BLOCKED):
        queryset = queryset.filter(status=status)
    order_fields = EMPLOYEE_SORT_OPTIONS.get(sort, EMPLOYEE_SORT_OPTIONS[DEFAULT_EMPLOYEE_SORT])
    return queryset.order_by(*order_fields)


def employee_list(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employees = User.objects.filter(role=User.Role.EMPLOYEE).annotate(
        course_count=Count("enrollments")
    )
    employees = filter_employees(employees, request.GET)
    paginator = Paginator(employees, 10)
    try:
        page_number = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "accounts/employee_list.html",
        {
            "employees": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": paginator.num_pages > 1,
            "nav_active": "employees",
            "q": request.GET.get("q", ""),
            "selected_status": request.GET.get("status", ""),
            "selected_sort": request.GET.get("sort", ""),
        },
    )


def edit_employee(request, pk):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "%s was updated." % employee.email)
            return redirect("admin_panel:employees")
    else:
        form = EmployeeUpdateForm(instance=employee)
    return render(
        request,
        "accounts/employee_edit.html",
        {"form": form, "employee": employee, "nav_active": "employees"},
    )


def employee_filter(request):
    if not request.user.is_authenticated or request.user.role != "admin":
        return JsonResponse({"results": []}, status=403)
    employees = User.objects.filter(role=User.Role.EMPLOYEE).annotate(
        course_count=Count("enrollments")
    )
    employees = filter_employees(employees, request.GET)
    paginator = Paginator(employees, 10)
    try:
        page_number = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)
    results = [
        {
            "id": employee.pk,
            "display_name": employee.display_name(),
            "email": employee.email,
            "initial": employee.initial(),
            "hue": employee.email[:1].lower(),
            "course_count": employee.course_count,
            "status": employee.status,
            "status_display": employee.get_status_display(),
        }
        for employee in page_obj.object_list
    ]
    return JsonResponse(
        {
            "results": results,
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "total_count": paginator.count,
        }
    )


def approve_employee(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:employees")
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    if employee.status == User.Status.APPROVED:
        return redirect("admin_panel:employees")
    employee.status = User.Status.APPROVED
    employee.save()
    sent = notify_employee_approved(employee)
    if sent:
        messages.success(request, "%s is approved." % employee.email)
    else:
        messages.warning(
            request,
            "%s is approved, but the email could not be sent." % employee.email,
        )
    return redirect("admin_panel:employees")


def block_employee(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:employees")
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    if employee.status == User.Status.BLOCKED:
        return redirect("admin_panel:employees")
    employee.status = User.Status.BLOCKED
    employee.save()
    sent = notify_employee_blocked(employee)
    if sent:
        messages.success(request, "%s cannot log in now." % employee.email)
    else:
        messages.warning(
            request,
            "%s is blocked, but the email could not be sent." % employee.email,
        )
    return redirect("admin_panel:employees")


def mail_action(request, action, token):
    if request.method != "GET":
        return _mail_page(request, False, "This email link is invalid.")
    token = token.rstrip("/")
    try:
        value = TimestampSigner(salt=MAIL_SALT, sep=MAIL_SEP).unsign(
            token, max_age=60 * 60 * 24 * 7
        )
    except (BadSignature, SignatureExpired):
        return _mail_page(
            request, False, "This email link is invalid or has expired."
        )
    parts = value.split(".", 1)
    if len(parts) != 2:
        return _mail_page(request, False, "This email link is invalid.")
    pk, signed_action = parts
    if signed_action != action or action not in ("approve", "block"):
        return _mail_page(request, False, "This email link is invalid.")
    employee = User.objects.filter(pk=pk, role=User.Role.EMPLOYEE).first()
    if employee is None:
        return _mail_page(request, False, "This email link is invalid.")
    if action == "approve":
        if employee.status == User.Status.APPROVED:
            return _mail_page(
                request,
                False,
                "This user is already approved. The Approve button can no longer be used.",
            )
        if employee.status == User.Status.BLOCKED:
            return _mail_page(
                request,
                False,
                "This user is already blocked. Email buttons can no longer be used.",
            )
        employee.status = User.Status.APPROVED
        employee.save()
        notify_employee_approved(employee)
        return _mail_page(request, True, "Approved successfully.")
    if employee.status == User.Status.BLOCKED:
        return _mail_page(
            request,
            False,
            "This user is already blocked. The Block button can no longer be used.",
        )
    if employee.status == User.Status.APPROVED:
        return _mail_page(
            request,
            False,
            "This user is already approved. Email buttons can no longer be used.",
        )
    employee.status = User.Status.BLOCKED
    employee.save()
    notify_employee_blocked(employee)
    return _mail_page(
        request, True, "%s is blocked and cannot log in." % employee.email
    )
