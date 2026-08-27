from django.conf import settings
from django.db import models


class Feedback(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        FEATURE = "feature", "New Feature"
        BUG = "bug", "Bug / Issue"
        COURSE_CONTENT = "course_content", "Course Content"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "Feedback from %s" % self.user
