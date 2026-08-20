from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, Enrollment


class DashboardTimelinessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            first_name="Ada",
        )
        self.emp_on_time = User.objects.create_user(
            email="ontime@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="On",
            status=User.Status.APPROVED,
        )
        self.emp_late = User.objects.create_user(
            email="late@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="Late",
            status=User.Status.APPROVED,
        )
        self.emp_overdue = User.objects.create_user(
            email="overdue@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="Rita",
            status=User.Status.APPROVED,
        )
        pdf = SimpleUploadedFile("course.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.course = Course.objects.create(
            title="Safety",
            description="QA training",
            pdf=pdf,
            created_by=self.admin,
        )
        now = timezone.now()
        Enrollment.objects.create(
            employee=self.emp_on_time,
            course=self.course,
            due_at=now + timedelta(days=1),
            completed_at=now - timedelta(hours=1),
        )
        Enrollment.objects.create(
            employee=self.emp_late,
            course=self.course,
            due_at=now - timedelta(days=2),
            completed_at=now - timedelta(days=1),
        )
        Enrollment.objects.create(
            employee=self.emp_overdue,
            course=self.course,
            due_at=now - timedelta(days=3),
        )

    def test_admin_dashboard_on_time_late_overdue_counts(self):
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["on_time_employees"], 1)
        self.assertEqual(response.context["on_time_assignments"], 1)
        self.assertEqual(response.context["late_employees"], 1)
        self.assertEqual(response.context["late_assignments"], 1)
        self.assertEqual(response.context["overdue_employees"], 1)
        self.assertEqual(response.context["overdue_assignments"], 1)
        self.assertContains(response, "Completed on time")
        self.assertContains(response, "Rita")
        self.assertEqual(response.context["kpi"], "overdue")
        self.assertEqual(response.context["kpi_rows"][0].employee, self.emp_overdue)
        self.assertNotContains(response, "Passed / Failed")
        self.assertNotContains(response, "Recent assignments")

    def test_same_employee_two_on_time_assignments(self):
        pdf = SimpleUploadedFile("two.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        course_two = Course.objects.create(
            title="Safety 2",
            description="More training",
            pdf=pdf,
            created_by=self.admin,
        )
        now = timezone.now()
        Enrollment.objects.create(
            employee=self.emp_on_time,
            course=course_two,
            due_at=now + timedelta(days=2),
            completed_at=now,
        )
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.context["on_time_employees"], 1)
        self.assertEqual(response.context["on_time_assignments"], 2)

    def test_kpi_card_shows_matching_rows(self):
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.get(reverse("core:dashboard"), {"kpi": "on_time"})
        self.assertEqual(response.context["kpi"], "on_time")
        self.assertEqual(response.context["kpi_rows"][0].employee, self.emp_on_time)
        self.assertContains(response, "Safety")
        late = self.client.get(reverse("core:dashboard"), {"kpi": "late"})
        self.assertEqual(late.context["kpi_rows"][0].employee, self.emp_late)
