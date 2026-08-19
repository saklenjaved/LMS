from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import urlparse

from apps.accounts.models import User


class LoginTests(TestCase):
    def test_login_with_email(self):
        User.objects.create_user(
            email="emp@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            status=User.Status.APPROVED,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "emp@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 302)

    def test_pending_employee_cannot_login(self):
        User.objects.create_user(
            email="wait@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "wait@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You are not approved by the admin yet",
        )

    def test_blocked_employee_cannot_login(self):
        User.objects.create_user(
            email="blocked@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            status=User.Status.BLOCKED,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "blocked@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "blocked by the admin")


class RegisterTests(TestCase):
    def test_register_employee_is_pending(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Sam",
                "last_name": "Lee",
                "email": "sam@example.com",
                "password1": "strongpass123",
                "password2": "strongpass123",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="sam@example.com")
        self.assertEqual(user.role, User.Role.EMPLOYEE)
        self.assertEqual(user.status, User.Status.PENDING)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="lms@example.com",
    DEFAULT_FROM_EMAIL="lms@example.com",
    SITE_URL="http://127.0.0.1:8000",
)
class ApprovalEmailTests(TestCase):
    def _register(self, email):
        self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Sam",
                "last_name": "Lee",
                "email": email,
                "password1": "strongpass123",
                "password2": "strongpass123",
            },
        )

    def _link_path(self, label):
        html = mail.outbox[0].alternatives[0][0]
        needle = 'href="'
        start = 0
        while True:
            i = html.find(needle, start)
            self.assertNotEqual(i, -1)
            href_start = i + len(needle)
            href_end = html.find('"', href_start)
            href = html[href_start:href_end]
            after = html[href_end : href_end + 200]
            if label in after:
                return urlparse(href).path
            start = href_end

    def test_register_emails_all_admins_from_database(self):
        User.objects.create_superuser(
            email="admin1@example.com", password="adminpass123"
        )
        User.objects.create_user(
            email="admin2@example.com",
            password="adminpass123",
            role=User.Role.ADMIN,
        )
        self._register("sam@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "New Employee Registration")
        self.assertIn("admin1@example.com", mail.outbox[0].to)
        self.assertIn("admin2@example.com", mail.outbox[0].to)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("Approve User", html)
        self.assertIn("Block User", html)
        self.assertIn("http://127.0.0.1:8000/accounts/mail/approve/", html)
        self.assertIn("http://127.0.0.1:8000/accounts/mail/block/", html)
        self.assertIn("http://127.0.0.1:8000/accounts/mail/approve/", mail.outbox[0].body)
        self.assertIn("http://127.0.0.1:8000/accounts/mail/block/", mail.outbox[0].body)

    def test_email_approve_link_works_without_login(self):
        User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self._register("sam@example.com")
        path = self._link_path("Approve User")
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved successfully")
        self.assertContains(response, "Returning to your email")
        self.assertNotContains(response, "Go to login")
        self.assertNotContains(response, "/accounts/login/")
        employee = User.objects.get(email="sam@example.com")
        self.assertEqual(employee.status, User.Status.APPROVED)
        self.assertEqual(mail.outbox[1].to, ["sam@example.com"])
        self.assertIn("approved successfully", mail.outbox[1].body.lower())
        login = self.client.post(
            reverse("accounts:login"),
            {"username": "sam@example.com", "password": "strongpass123"},
        )
        self.assertEqual(login.status_code, 302)

    def test_email_block_link_works_without_login(self):
        User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self._register("sam@example.com")
        path = self._link_path("Block User")
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot log in")
        employee = User.objects.get(email="sam@example.com")
        self.assertEqual(employee.status, User.Status.BLOCKED)
        self.assertEqual(mail.outbox[1].to, ["sam@example.com"])
        self.assertIn("blocked by the admin", mail.outbox[1].body)
        login = self.client.post(
            reverse("accounts:login"),
            {"username": "sam@example.com", "password": "strongpass123"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertContains(login, "blocked by the admin")

    def test_tampered_email_link_is_rejected(self):
        User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self._register("sam@example.com")
        path = self._link_path("Approve User")
        parts = path.rstrip("/").split("/")
        parts[-1] = parts[-1][:-4] + "xxxx"
        tampered = "/".join(parts) + "/"
        response = self.client.get(tampered)
        self.assertContains(response, "invalid or has expired")
        employee = User.objects.get(email="sam@example.com")
        self.assertEqual(employee.status, User.Status.PENDING)

    def test_already_approved_link_does_not_email_again(self):
        User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self._register("sam@example.com")
        path = self._link_path("Approve User")
        self.client.get(path)
        self.assertEqual(len(mail.outbox), 2)
        response = self.client.get(path)
        self.assertContains(response, "already approved")
        self.assertContains(response, "can no longer be used")
        self.assertEqual(len(mail.outbox), 2)
        block_path = self._link_path("Block User")
        self.client.get(block_path)
        employee = User.objects.get(email="sam@example.com")
        self.assertEqual(employee.status, User.Status.APPROVED)

    def test_approve_emails_employee_once(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        employee = User.objects.create_user(
            email="emp@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
        )
        self.client.force_login(admin)
        self.client.post(reverse("accounts:approve_employee", args=[employee.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["emp@example.com"])
        self.client.post(reverse("accounts:approve_employee", args=[employee.pk]))
        self.assertEqual(len(mail.outbox), 1)

