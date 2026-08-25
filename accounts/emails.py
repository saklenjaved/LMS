import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner
from django.urls import reverse

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
    token = TimestampSigner(salt=RESET_SALT, sep=MAIL_SEP).sign(str(user.pk))
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

