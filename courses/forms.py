from django import forms

from accounts.models import User

from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "pdf"]


class AssignCourseForm(forms.Form):
    employees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE),
        widget=forms.CheckboxSelectMultiple,
    )
    due_at = forms.DateTimeField(
        label="Due time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )


class BulkAssignForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.all())
    employees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE),
        widget=forms.CheckboxSelectMultiple,
    )
    due_at = forms.DateTimeField(
        label="Due time",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )


class QuizAttemptForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions or [])
        for question in self.questions:
            self.fields["q_%s" % question.pk] = forms.ChoiceField(
                label=question.question_text,
                choices=[(str(opt.pk), opt.option_text) for opt in question.options.all()],
                widget=forms.RadioSelect,
            )
