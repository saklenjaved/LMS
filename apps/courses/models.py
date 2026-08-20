from django.conf import settings
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    pdf = models.FileField(upload_to="courses/pdfs/")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()


class QuizOption(models.Model):
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        COMPLETED = "completed", "Completed"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "employee"},
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    quiz_taken_at = models.DateTimeField(null=True, blank=True)
    quiz_correct = models.PositiveIntegerField(default=0)
    quiz_wrong = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("employee", "course"),
                name="unique_employee_course",
            )
        ]
