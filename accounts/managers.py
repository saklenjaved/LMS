from django.contrib.auth.models import BaseUserManager


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
