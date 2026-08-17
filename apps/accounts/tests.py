from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class LoginTests(TestCase):
    def test_login_with_email(self):
        User.objects.create_user(
            email="emp@example.com", password="pass12345", role=User.Role.EMPLOYEE
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "emp@example.com", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 302)
