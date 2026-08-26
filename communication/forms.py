from django import forms

from .models import Conversation, Feedback, Message


class ConversationForm(forms.ModelForm):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
        label="Message",
    )

    class Meta:
        model = Conversation
        fields = ["subject"]
        widgets = {"subject": forms.TextInput(attrs={"class": "form-control"})}


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "class": "form-control"})}


class FeedbackForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(n, str(n)) for n in range(1, 6)],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Feedback
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={"rows": 3, "class": "form-control", "placeholder": "Optional comment"}
            )
        }
