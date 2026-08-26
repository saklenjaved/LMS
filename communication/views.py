from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ConversationForm, FeedbackForm, MessageForm
from .models import Conversation, Message


def _employee_required(request):
    return request.user.is_authenticated and request.user.role == "employee"


def _admin_required(request):
    return request.user.is_authenticated and request.user.role == "admin"


def conversation_list(request):
    if not _employee_required(request):
        return redirect("core:dashboard")
    conversations = Conversation.objects.filter(employee=request.user)
    paginator = Paginator(conversations, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "communication/conversation_list.html",
        {"nav_active": "communication", "page_obj": page_obj, "conversations": page_obj},
    )


def conversation_create(request):
    if not _employee_required(request):
        return redirect("core:dashboard")
    if request.method == "GET":
        return render(
            request,
            "communication/conversation_form.html",
            {"nav_active": "communication", "form": ConversationForm()},
        )
    form = ConversationForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "communication/conversation_form.html",
            {"nav_active": "communication", "form": form},
        )
    conversation = form.save(commit=False)
    conversation.employee = request.user
    conversation.save()
    Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body=form.cleaned_data["body"],
    )
    messages.success(request, "Conversation started.")
    return redirect("communication:detail", pk=conversation.pk)


def conversation_detail(request, pk):
    if not _employee_required(request):
        return redirect("core:dashboard")
    conversation = get_object_or_404(Conversation, pk=pk, employee=request.user)
    is_open = conversation.status == Conversation.Status.OPEN

    if request.method == "POST" and is_open:
        if "send_message" in request.POST:
            message_form = MessageForm(request.POST)
            if message_form.is_valid():
                message = message_form.save(commit=False)
                message.conversation = conversation
                message.sender = request.user
                message.save()
                return redirect("communication:detail", pk=conversation.pk)
        elif "submit_feedback" in request.POST:
            feedback_form = FeedbackForm(request.POST)
            if feedback_form.is_valid():
                feedback = feedback_form.save(commit=False)
                feedback.conversation = conversation
                feedback.save()
                conversation.status = Conversation.Status.CLOSED
                conversation.closed_at = timezone.now()
                conversation.save()
                messages.success(request, "Conversation closed. Thanks for your feedback.")
                return redirect("communication:detail", pk=conversation.pk)

    return render(
        request,
        "communication/conversation_detail.html",
        {
            "nav_active": "communication",
            "conversation": conversation,
            "is_open": is_open,
            "message_form": MessageForm(),
            "feedback_form": FeedbackForm(),
        },
    )


def admin_conversation_list(request):
    if not _admin_required(request):
        return redirect("core:dashboard")
    conversations = Conversation.objects.select_related("employee", "admin")
    status = request.GET.get("status", "")
    if status in Conversation.Status.values:
        conversations = conversations.filter(status=status)
    paginator = Paginator(conversations, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "communication/admin_conversation_list.html",
        {
            "nav_active": "conversations",
            "page_obj": page_obj,
            "conversations": page_obj,
            "selected_status": status,
        },
    )


def admin_conversation_detail(request, pk):
    if not _admin_required(request):
        return redirect("core:dashboard")
    conversation = get_object_or_404(
        Conversation.objects.select_related("employee", "admin"), pk=pk
    )
    is_open = conversation.status == Conversation.Status.OPEN

    if request.method == "POST" and is_open:
        message_form = MessageForm(request.POST)
        if message_form.is_valid():
            message = message_form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            if conversation.admin_id is None:
                conversation.admin = request.user
                conversation.save()
            return redirect("admin_panel:conversation_detail", pk=conversation.pk)

    return render(
        request,
        "communication/admin_conversation_detail.html",
        {
            "nav_active": "conversations",
            "conversation": conversation,
            "is_open": is_open,
            "message_form": MessageForm(),
        },
    )
