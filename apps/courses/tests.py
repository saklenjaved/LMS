from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

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
            employee=self.employee, course=self.course
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
        self.assertContains(review, "Well done")
        review_again = self.client.get(
            reverse("courses:quiz_review", args=[self.enrollment.pk])
        )
        self.assertContains(review_again, "Show certificate")
        self.assertNotContains(review_again, "Well done")
        self.client.post(reverse("courses:quiz", args=[self.enrollment.pk]), data)
        review_retry = self.client.get(
            reverse("courses:quiz_review", args=[self.enrollment.pk])
        )
        self.assertNotContains(review_retry, "Well done")
        cert = self.client.get(reverse("courses:certificate", args=[self.enrollment.pk]))
        self.assertEqual(cert.status_code, 200)
        self.assertContains(cert, "Print")
        self.assertContains(cert, "Back")
        self.assertContains(cert, "Certificate of Completion")

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

    def test_admin_sidebar_pages_load(self):
        self.client.login(email="admin@example.com", password="pass12345")
        for name in (
            "core:dashboard",
            "core:reports",
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
