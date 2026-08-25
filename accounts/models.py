from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        EMPLOYEE = "employee", "Employee"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        BLOCKED = "blocked", "Blocked"

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    def display_name(self):
        name = ("%s %s" % (self.first_name or "", self.last_name or "")).strip()
        if name:
            return name
        return self.email or "User"

    def sidebar_name(self):
        name = ("%s %s" % (self.first_name or "", self.last_name or "")).strip()
        if name:
            return name
        return self.get_role_display()

    def initial(self):
        name = self.sidebar_name()
        if name:
            return name[0].upper()
        return "U"
