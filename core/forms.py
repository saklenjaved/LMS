from django import forms

from .models import Feedback


class FeedbackForm(forms.ModelForm):
    RATING_CHOICES = [
        ("", "No rating"),
        (5, "5 - Excellent"),
        (4, "4 - Good"),
        (3, "3 - Okay"),
        (2, "2 - Poor"),
        (1, "1 - Bad"),
    ]

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        required=False,
        empty_value=None,
        label="Overall experience",
    )

    class Meta:
        model = Feedback
        fields = ["rating", "message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Tell us how your experience with the LMS is going...",
                }
            ),
        }
        labels = {"message": "Your feedback"}
