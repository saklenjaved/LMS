from django.contrib import admin

from .models import Feedback

admin.site.site_header = "LMS Admin"


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("user__email", "message")
    readonly_fields = ("user", "category", "message", "created_at")
