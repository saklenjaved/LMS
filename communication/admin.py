from django.contrib import admin

from .models import Conversation, Feedback, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "body", "sent_at")


class FeedbackInline(admin.StackedInline):
    model = Feedback
    extra = 0
    readonly_fields = ("rating", "comment", "submitted_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("subject", "employee", "admin", "status", "created_at")
    list_filter = ("status",)
    inlines = [MessageInline, FeedbackInline]
