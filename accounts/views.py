import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    EmailAuthenticationForm,
    EmployeeUpdateForm,
    NewPasswordForm,
    PasswordResetForm,
    RegisterForm,
)
from .models import User

logger = logging.getLogger(__name__)

MAIL_SALT = "lms-mail-action"
MAIL_SEP = "."
RESET_SALT = "lms-password-reset"


def _admin_emails():
    return list(
        User.objects.filter(role=User.Role.ADMIN)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )


def _from_email():
    return settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or "lms@localhost"


def _can_send():
    backend = settings.EMAIL_BACKEND or ""
    if "console" in backend or "locmem" in backend:
        return True
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def _site_base():
    return (settings.SITE_URL or "http://127.0.0.1:8000").rstrip("/")


def mail_token(pk, action):
    return TimestampSigner(salt=MAIL_SALT, sep=MAIL_SEP).sign(
        "%s.%s" % (pk, action)
    )


def mail_action_url(pk, action, base):
    token = mail_token(pk, action)
    path = reverse("accounts:mail_action", args=[action, token])
    return base.rstrip("/") + path


def notify_admin_new_employee(employee):
    to_emails = _admin_emails()
    if not to_emails:
        logger.error("No admin users with an email were found.")
        return False
    if not _can_send():
        logger.error(
            "SMTP is not set. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env"
        )
        return False
    name = employee.get_full_name() or employee.email
    base = _site_base()
    approve_url = mail_action_url(employee.pk, "approve", base)
    block_url = mail_action_url(employee.pk, "block", base)
    text = (
        "New Employee Registration\n\n"
        "An employee has registered and is waiting for your approval.\n\n"
        "Employee Name: %s\n"
        "Employee Email: %s\n\n"
        "Approve User:\n%s\n\n"
        "Block User:\n%s\n"
    ) % (
        name,
        employee.email,
        approve_url,
        block_url,
    )
    html = """
    <div style="font-family:Arial,sans-serif;max-width:520px">
      <h2 style="margin:0 0 12px">New Employee Registration</h2>
      <p>An employee has registered and is waiting for your approval.</p>
      <p>
        <b>Employee Name:</b> {name}<br>
        <b>Employee Email:</b> {email}
      </p>
      <p>Tap a button. No LMS login is needed.</p>
      <table cellpadding="0" cellspacing="0" style="margin:16px 0">
        <tr>
          <td style="background:#16a34a;border-radius:6px">
            <a href="{approve}" style="display:inline-block;padding:12px 22px;color:#fff;text-decoration:none;font-weight:bold">
              Approve User
            </a>
          </td>
          <td width="12"></td>
          <td style="background:#dc2626;border-radius:6px">
            <a href="{block}" style="display:inline-block;padding:12px 22px;color:#fff;text-decoration:none;font-weight:bold">
              Block User
            </a>
          </td>
        </tr>
      </table>
      <p style="color:#64748b;font-size:13px;word-break:break-all">
        If the buttons do not open, copy a link into your browser:<br>
        Approve User:<br>
        <a href="{approve}">{approve}</a><br><br>
        Block User:<br>
        <a href="{block}">{block}</a>
      </p>
    </div>
    """.format(
        name=name,
        email=employee.email,
        approve=approve_url,
        block=block_url,
    )
    try:
        mail = EmailMultiAlternatives(
            subject="New Employee Registration",
            body=text,
            from_email=_from_email(),
            to=to_emails,
        )
        mail.attach_alternative(html, "text/html")
        mail.send()
        return True
    except Exception:
        logger.exception("Could not send new-employee email to admin.")
        return False


def notify_employee_approved(employee):
    if not _can_send():
        logger.error(
            "SMTP is not set. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env"
        )
        return False
    name = employee.get_full_name() or employee.email
    try:
        mail = EmailMultiAlternatives(
            subject="Your LMS Account Has Been Approved Successfully",
            body=(
                "Hello %s,\n\n"
                "Your account has been approved successfully.\n\n"
                "Thank you."
            )
            % name,
            from_email=_from_email(),
            to=[employee.email],
        )
        mail.send()
        return True
    except Exception:
        logger.exception("Could not send approval email to %s.", employee.email)
        return False


def notify_employee_blocked(employee):
    if not _can_send():
        logger.error(
            "SMTP is not set. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env"
        )
        return False
    name = employee.get_full_name() or employee.email
    try:
        mail = EmailMultiAlternatives(
            subject="Your LMS Account Has Been Blocked",
            body=(
                "Hello %s,\n\n"
                "Your account has been blocked by the admin.\n\n"
                "You cannot log in to the LMS.\n\n"
                "Thank you."
            )
            % name,
            from_email=_from_email(),
            to=[employee.email],
        )
        mail.send()
        return True
    except Exception:
        logger.exception("Could not send blocked email to %s.", employee.email)
        return False


def notify_course_assigned(employee, course, enrollment=None):
    if not employee.email:
        return False
    if not _can_send():
        logger.error(
            "SMTP is not set. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env"
        )
        return False
    name = employee.get_full_name() or employee.email
    pdf_name = "No PDF"
    if course.pdf:
        pdf_name = course.pdf.name.split("/")[-1]
    due_text = enrollment.due_at.strftime("%Y-%m-%d %H:%M") if enrollment else ""
    assigned_text = ""
    if enrollment and enrollment.assigned_at:
        assigned_text = enrollment.assigned_at.strftime("%Y-%m-%d %H:%M")
    else:
        assigned_text = "Just now"
    login_url = _site_base() + reverse("accounts:login")
    text = (
        "Hello %s,\n\n"
        "A new course has been assigned to you.\n\n"
        "Course title: %s\n"
        "PDF file: %s\n"
        "Assigned at: %s\n"
        "Due time: %s\n\n"
        "Log in to LMS: %s\n\n"
        "Thank you."
    ) % (
        name,
        course.title,
        pdf_name,
        assigned_text,
        due_text,
        login_url,
    )
    html = """
    <div style="font-family:Arial,sans-serif;max-width:520px">
      <h2 style="margin:0 0 12px">New Course Assigned</h2>
      <p>Hello {name},</p>
      <p>A new course has been assigned to you. Here are the course details:</p>
      <p>
        <b>Course title:</b> {title}<br>
        <b>PDF file:</b> {pdf}<br>
        <b>Assigned at:</b> {assigned}<br>
        <b>Due time:</b> {due}
      </p>
      <p><a href="{login}">Log in to LMS</a></p>
    </div>
    """.format(
        name=name,
        title=course.title,
        pdf=pdf_name,
        assigned=assigned_text,
        due=due_text,
        login=login_url,
    )
    try:
        mail = EmailMultiAlternatives(
            subject="New LMS Course Assigned: %s" % course.title,
            body=text,
            from_email=_from_email(),
            to=[employee.email],
        )
        mail.attach_alternative(html, "text/html")
        mail.send()
        return True
    except Exception:
        logger.exception("Could not send course email to %s.", employee.email)
        return False


def notify_password_reset(user):
    if not user.email:
        return False
    if not _can_send():
        logger.error(
            "SMTP is not set. Add EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env"
        )
        return False
    name = user.get_full_name() or user.email
    payload = "%s%s%s" % (user.pk, MAIL_SEP, user.password)
    token = TimestampSigner(salt=RESET_SALT, sep=MAIL_SEP).sign(payload)
    reset_url = _site_base() + reverse("accounts:password_reset_confirm", args=[token])
    text = (
        "Hello %s,\n\n"
        "You asked to reset your LMS password.\n\n"
        "Open this link to choose a new password:\n%s\n\n"
        "If you did not ask for this, you can ignore this email.\n"
    ) % (name, reset_url)
    html = """
    <div style="font-family:Arial,sans-serif;max-width:520px">
      <h2 style="margin:0 0 12px">Reset your LMS password</h2>
      <p>Hello {name},</p>
      <p>You asked to reset your LMS password.</p>
      <p><a href="{url}">Choose a new password</a></p>
      <p>If you did not ask for this, you can ignore this email.</p>
    </div>
    """.format(name=name, url=reset_url)
    try:
        mail = EmailMultiAlternatives(
            subject="Reset your LMS password",
            body=text,
            from_email=_from_email(),
            to=[user.email],
        )
        mail.attach_alternative(html, "text/html")
        mail.send()
        return True
    except Exception:
        logger.exception("Could not send password reset email to %s.", user.email)
        return False


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
    if user and user.password_reset_used:
        messages.error(
            request,
            "You have already used your one-time password reset. "
            "Ask your admin to reset your password.",
        )
        return redirect("accounts:login")
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
    if user.password_reset_used:
        messages.error(
            request,
            "You have already used your one-time password reset. "
            "Ask your admin to reset your password.",
        )
        return redirect("accounts:login")
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
    user.password_reset_used = True
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


def allow_password_reset(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:employees")
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.role != "admin":
        return redirect("core:dashboard")
    employee = get_object_or_404(User, pk=pk, role=User.Role.EMPLOYEE)
    employee.password_reset_used = False
    employee.save(update_fields=["password_reset_used"])
    messages.success(
        request,
        "%s can use forgot password once more." % employee.email,
    )
    return redirect("admin_panel:edit_employee", pk=employee.pk)


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
