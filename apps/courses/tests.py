from datetime import timedelta

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Course, Enrollment, QuizOption, QuizQuestion


class AccountsTests(TestCase):
    def test_register_creates_employee(self):
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
        self.assertEqual(user.status, user.Status.PENDING)


class CourseFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="pass12345",
            role=User.Role.ADMIN,
            first_name="Ada",
        )
        self.employee = User.objects.create_user(
            email="emp@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="Eli",
            status=User.Status.APPROVED,
        )
        pdf = SimpleUploadedFile("course.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        self.course = Course.objects.create(
            title="Python Basics",
            description="Intro",
            pdf=pdf,
            created_by=self.admin,
        )
        for i in range(4):
            question = QuizQuestion.objects.create(
                course=self.course,
                question_text=f"Question {i + 1}?",
            )
            QuizOption.objects.create(question=question, option_text="A", is_correct=True)
            QuizOption.objects.create(question=question, option_text="B", is_correct=False)
            QuizOption.objects.create(question=question, option_text="C", is_correct=False)
            QuizOption.objects.create(question=question, option_text="D", is_correct=False)
        self.enrollment = Enrollment.objects.create(
            employee=self.employee,
            course=self.course,
            due_at=timezone.now() + timedelta(days=7),
        )

    def test_employee_cannot_quiz_before_complete(self):
        self.client.login(email="emp@example.com", password="pass12345")
        response = self.client.get(reverse("courses:quiz", args=[self.enrollment.pk]))
        self.assertEqual(response.status_code, 302)

    def test_pass_quiz_unlocks_certificate(self):
        self.enrollment.status = Enrollment.Status.COMPLETED
        self.enrollment.save()
        self.client.login(email="emp@example.com", password="pass12345")
        data = {}
        for q in self.course.questions.all():
            data["q_%s" % q.pk] = str(q.options.get(is_correct=True).pk)
        response = self.client.post(
            reverse("courses:quiz", args=[self.enrollment.pk]), data
        )
        self.assertRedirects(
            response,
            reverse("courses:quiz_review", args=[self.enrollment.pk]),
            fetch_redirect_response=False,
        )
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.PASSED)
        self.assertEqual(self.enrollment.quiz_correct, 4)
        self.assertEqual(self.enrollment.quiz_wrong, 0)
        review = self.client.get(reverse("courses:quiz_review", args=[self.enrollment.pk]))
        self.assertContains(review, "Correct")
        self.assertContains(review, "Show certificate")
        self.assertContains(review, "Certificate unlocked")
        self.assertContains(review, "Open certificate")
        self.assertContains(review, "History")
        review_again = self.client.get(
            reverse("courses:quiz_review", args=[self.enrollment.pk])
        )
        self.assertContains(review_again, "Show certificate")
        self.assertNotContains(review_again, "Certificate unlocked")
        self.client.post(reverse("courses:quiz", args=[self.enrollment.pk]), data)
        review_retry = self.client.get(
            reverse("courses:quiz_review", args=[self.enrollment.pk])
        )
        self.assertNotContains(review_retry, "Certificate unlocked")
        cert = self.client.get(reverse("courses:certificate", args=[self.enrollment.pk]))
        self.assertEqual(cert.status_code, 200)
        self.assertContains(cert, "Print")
        self.assertContains(cert, "Download PDF")
        self.assertContains(cert, "My History")
        self.assertContains(cert, "Certificate of Completion")
        pdf = self.client.get(
            reverse("courses:certificate_pdf", args=[self.enrollment.pk])
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        history = self.client.get(reverse("courses:history"))
        self.assertContains(history, "Python Basics")
        self.assertContains(history, "Show certificate")

    def test_fail_quiz_no_certificate(self):
        self.enrollment.status = Enrollment.Status.COMPLETED
        self.enrollment.save()
        self.client.login(email="emp@example.com", password="pass12345")
        questions = list(self.course.questions.all())
        data = {}
        for q in questions:
            data["q_%s" % q.pk] = str(q.options.get(is_correct=True).pk)
        wrong = questions[0].options.filter(is_correct=False).first()
        data["q_%s" % questions[0].pk] = str(wrong.pk)
        self.client.post(reverse("courses:quiz", args=[self.enrollment.pk]), data)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.Status.FAILED)
        self.assertEqual(self.enrollment.quiz_correct, 3)
        self.assertEqual(self.enrollment.quiz_wrong, 1)
        review = self.client.get(reverse("courses:quiz_review", args=[self.enrollment.pk]))
        self.assertContains(review, "Wrong")
        self.assertNotContains(review, "Well done")
        cert = self.client.get(reverse("courses:certificate", args=[self.enrollment.pk]))
        self.assertEqual(cert.status_code, 302)

    def test_admin_sees_courses_employee_does_not(self):
        self.client.login(email="emp@example.com", password="pass12345")
        response = self.client.get(reverse("courses:list"))
        self.assertEqual(response.status_code, 302)
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.get(reverse("courses:list"))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_course(self):
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.get(reverse("courses:view", args=[self.course.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Basics")
        self.assertContains(response, "Intro")
        self.assertContains(response, "Open PDF")
        self.client.login(email="emp@example.com", password="pass12345")
        blocked = self.client.get(reverse("courses:view", args=[self.course.pk]))
        self.assertEqual(blocked.status_code, 302)
        self.client.login(email="admin@example.com", password="pass12345")
        for name in (
            "core:dashboard",
            "core:reports",
            "analytics",
            "accounts:employees",
            "courses:list",
            "courses:enrollments",
            "courses:assignments",
            "courses:quiz_results",
            "courses:quizzes",
        ):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_admin_can_edit_and_delete_quiz_question(self):
        self.client.login(email="admin@example.com", password="pass12345")
        question = self.course.questions.first()
        response = self.client.post(
            reverse("courses:quiz_edit", args=[question.pk]),
            {
                "question_text": "Updated question?",
                "option_1": "A",
                "option_2": "B",
                "option_3": "C",
                "option_4": "D",
                "extra": "0",
                "correct": "2",
            },
        )
        self.assertEqual(response.status_code, 302)
        question.refresh_from_db()
        self.assertEqual(question.question_text, "Updated question?")
        self.client.post(reverse("courses:quiz_delete", args=[self.course.pk]))
        self.assertEqual(self.course.questions.count(), 0)

    def test_employee_dashboard_has_courses_and_history(self):
        self.client.login(email="emp@example.com", password="pass12345")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My courses")
        self.assertContains(response, "History")
        self.assertContains(response, "LMS")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="lms@example.com",
        DEFAULT_FROM_EMAIL="lms@example.com",
        SITE_URL="http://127.0.0.1:8000",
    )
    def test_assign_course_emails_employee_details(self):
        other = User.objects.create_user(
            email="newemp@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="Nina",
            status=User.Status.APPROVED,
        )
        due = timezone.now().replace(microsecond=0) + timedelta(days=7)
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.post(
            reverse("courses:assignments"),
            {
                "course": self.course.pk,
                "employees": [other.pk],
                "due_at": due.strftime("%Y-%m-%dT%H:%M"),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["newemp@example.com"])
        self.assertIn("Python Basics", sent.subject)
        self.assertIn("Python Basics", sent.body)
        self.assertNotIn("Intro", sent.body)
        self.assertNotIn("Description:", sent.body)
        self.assertNotIn("Quiz questions:", sent.body)
        self.assertIn("PDF file:", sent.body)
        self.assertIn(".pdf", sent.body)
        self.assertIn("Due time:", sent.body)
        self.assertIn("Assigned at:", sent.body)
        enrollment = Enrollment.objects.get(employee=other, course=self.course)
        self.assertIsNotNone(enrollment.due_at)

    def test_assign_course_requires_due_at(self):
        other = User.objects.create_user(
            email="nodue@example.com",
            password="pass12345",
            role=User.Role.EMPLOYEE,
            first_name="Ned",
            status=User.Status.APPROVED,
        )
        self.client.login(email="admin@example.com", password="pass12345")
        response = self.client.post(
            reverse("courses:assignments"),
            {
                "course": self.course.pk,
                "employees": [other.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Enrollment.objects.filter(employee=other, course=self.course).exists()
        )
