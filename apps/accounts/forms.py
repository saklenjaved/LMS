from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django import forms

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EMPLOYEE
        user.status = User.Status.PENDING
        if commit:
            user.save()
        return user
