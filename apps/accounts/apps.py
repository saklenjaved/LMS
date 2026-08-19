from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from allauth.socialaccount.providers.google.provider import GoogleProvider

        from .adapters import LmsGoogleOAuth2Adapter

        GoogleProvider.oauth2_adapter_class = LmsGoogleOAuth2Adapter
