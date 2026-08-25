from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

from .models import User


class LmsAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False


class LmsSocialAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return False

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ):
        messages.error(
            request,
            "Google authentication failed. Please try again.",
        )
        raise ImmediateHttpResponse(redirect("accounts:login"))

    def pre_social_login(self, request, sociallogin):
        extra = sociallogin.account.extra_data or {}
        email = (extra.get("email") or "").strip().lower()
        verified = extra.get("email_verified")
        if verified is None:
            verified = extra.get("verified_email")
        for addr in sociallogin.email_addresses:
            if addr.email:
                email = addr.email.strip().lower()
            if addr.verified:
                verified = True
        if not email or verified is not True:
            messages.error(
                request,
                "Google authentication failed. Please try again.",
            )
            raise ImmediateHttpResponse(redirect("accounts:login"))
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            messages.error(
                request,
                "This Google account is not registered in the LMS. Please register first.",
            )
            raise ImmediateHttpResponse(redirect("accounts:login"))
        if user.role == User.Role.EMPLOYEE and user.status == User.Status.PENDING:
            messages.error(
                request,
                "Your account is still waiting for administrator approval.",
            )
            raise ImmediateHttpResponse(redirect("accounts:login"))
        if user.role == User.Role.EMPLOYEE and user.status == User.Status.BLOCKED:
            messages.error(
                request,
                "Your account has been blocked by the admin. You cannot log in.",
            )
            raise ImmediateHttpResponse(redirect("accounts:login"))
        if not sociallogin.is_existing:
            sociallogin.connect(request, user)


class LmsGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    def get_callback_url(self, request, app):
        return settings.SITE_URL.rstrip("/") + reverse("google_callback")
