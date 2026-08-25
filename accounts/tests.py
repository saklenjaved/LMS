from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import urlparse

from accounts.models import User


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
        self.client.post(reverse("admin_panel:approve_employee", args=[employee.pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["emp@example.com"])
        self.client.post(reverse("admin_panel:approve_employee", args=[employee.pk]))
        self.assertEqual(len(mail.outbox), 1)


class GoogleLoginTests(TestCase):
    def _request(self):
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        if not self.client.session.session_key:
            self.client.get(reverse("accounts:login"))
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return request

    def _sociallogin(self, email, verified=True):
        from allauth.socialaccount.models import SocialAccount, SocialLogin

        account = SocialAccount(
            provider="google",
            uid="google-" + email,
            extra_data={"email": email, "email_verified": verified},
        )
        return SocialLogin(account=account)

    def test_login_page_has_google_button(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "OR")

    def test_unknown_google_email_does_not_create_user(self):
        from allauth.core.exceptions import ImmediateHttpResponse

        from accounts.adapters import LmsSocialAdapter

        adapter = LmsSocialAdapter()
        with self.assertRaises(ImmediateHttpResponse):
            adapter.pre_social_login(
                self._request(),
                self._sociallogin("gnew@example.com"),
            )
        self.assertFalse(User.objects.filter(email="gnew@example.com").exists())

    def test_pending_employee_cannot_google_login(self):
        from allauth.core.exceptions import ImmediateHttpResponse

        from accounts.adapters import LmsSocialAdapter

        User.objects.create_user(
            email="gwait@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            status=User.Status.PENDING,
        )
        adapter = LmsSocialAdapter()
        with self.assertRaises(ImmediateHttpResponse):
            adapter.pre_social_login(
                self._request(),
                self._sociallogin("gwait@example.com"),
            )

    def test_google_callback_url_uses_site_url(self):
        from django.test import RequestFactory

        from accounts.adapters import LmsGoogleOAuth2Adapter

        request = RequestFactory().get("/")
        adapter = LmsGoogleOAuth2Adapter(request)
        self.assertEqual(
            adapter.get_callback_url(request, app=None),
            "http://127.0.0.1:8000/accounts/google/login/callback/",
        )

    def test_localhost_redirects_to_site_url(self):
        response = self.client.get("/accounts/login/", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("http://127.0.0.1:8000/"))

    def test_approved_employee_can_google_login(self):
        from accounts.adapters import LmsSocialAdapter

        user = User.objects.create_user(
            email="gemp@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            status=User.Status.APPROVED,
        )
        sociallogin = self._sociallogin("gemp@example.com")
        LmsSocialAdapter().pre_social_login(self._request(), sociallogin)
        self.assertEqual(sociallogin.user, user)
        user.refresh_from_db()
        self.assertTrue(user.has_usable_password())
        self.assertTrue(user.check_password("pass12345"))

    def test_admin_role_can_use_django_admin(self):
        admin = User.objects.create_user(
            email="staffadmin@example.com",
            password="adminpass123",
            role=User.Role.ADMIN,
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password("adminpass123"))


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST_USER="lms@example.com",
    DEFAULT_FROM_EMAIL="lms@example.com",
    SITE_URL="http://127.0.0.1:8000",
)
class PasswordResetTests(TestCase):
    def test_login_page_has_forgot_password_link(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "Forgot password?")
        self.assertContains(response, reverse("accounts:password_reset"))

    def test_unknown_email_does_not_send(self):
        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": "missing@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_sets_new_password(self):
        User.objects.create_user(
            email="emp@example.com",
            password="oldpass123",
            role=User.Role.EMPLOYEE,
            status=User.Status.APPROVED,
        )
        self.client.post(
            reverse("accounts:password_reset"),
            {"email": "emp@example.com"},
        )
        self.assertEqual(len(mail.outbox), 1)
        html = mail.outbox[0].alternatives[0][0]
        start = html.find('href="') + 6
        end = html.find('"', start)
        path = urlparse(html[start:end]).path
        response = self.client.post(
            path,
            {"password1": "newpass12345", "password2": "newpass12345"},
        )
        self.assertEqual(response.status_code, 302)
        login = self.client.post(
            reverse("accounts:login"),
            {"username": "emp@example.com", "password": "newpass12345"},
        )
        self.assertEqual(login.status_code, 302)

    def test_reset_link_cannot_be_reused(self):
        User.objects.create_user(
            email="emp2@example.com",
            password="oldpass123",
            role=User.Role.EMPLOYEE,
            status=User.Status.APPROVED,
        )
        self.client.post(
            reverse("accounts:password_reset"),
            {"email": "emp2@example.com"},
        )
        html = mail.outbox[0].alternatives[0][0]
        start = html.find('href="') + 6
        end = html.find('"', start)
        path = urlparse(html[start:end]).path
        first = self.client.post(
            path,
            {"password1": "newpass12345", "password2": "newpass12345"},
        )
        self.assertEqual(first.status_code, 302)
        second = self.client.post(
            path,
            {"password1": "anotherpass999", "password2": "anotherpass999"},
        )
        self.assertRedirects(second, reverse("accounts:password_reset"))
        login = self.client.post(
            reverse("accounts:login"),
            {"username": "emp2@example.com", "password": "newpass12345"},
        )
        self.assertEqual(login.status_code, 302)


