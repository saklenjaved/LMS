from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Count
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
from .forms import EmailAuthenticationForm, NewPasswordForm, PasswordResetForm, RegisterForm
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
        pk = TimestampSigner(salt=RESET_SALT, sep=MAIL_SEP).unsign(
            token, max_age=60 * 60 * 24
        )
    except (BadSignature, SignatureExpired):
        messages.error(request, "This reset link is invalid or has expired.")
        return redirect("accounts:password_reset")
    user = User.objects.filter(pk=pk).first()
    if user is None:
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


def employee_list(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employees = (
        User.objects.filter(role=User.Role.EMPLOYEE)
        .annotate(course_count=Count("enrollments"))
        .order_by("status", "first_name", "email")
    )
    return render(
        request,
        "accounts/employee_list.html",
        {"employees": employees, "nav_active": "employees"},
    )


def approve_employee(request, pk):
    if request.method != "POST":
        return redirect("accounts:employees")
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    if employee.status == User.Status.APPROVED:
        return redirect("accounts:employees")
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
    return redirect("accounts:employees")


def block_employee(request, pk):
    if request.method != "POST":
        return redirect("accounts:employees")
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    if employee.status == User.Status.BLOCKED:
        return redirect("accounts:employees")
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
    return redirect("accounts:employees")


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
