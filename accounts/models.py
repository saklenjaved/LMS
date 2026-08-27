from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not extra.get("role"):
            extra["role"] = "employee"
        if extra.get("role") == "admin":
            extra.setdefault("status", "approved")
            extra.setdefault("is_staff", True)
            extra.setdefault("is_superuser", True)
        else:
            extra.setdefault("status", "pending")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra):
        extra["is_staff"] = True
        extra["is_superuser"] = True
        extra["role"] = "admin"
        extra["status"] = "approved"
        return self.create_user(email, password, **extra)


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
    password_reset_used = models.BooleanField(default=False)

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
