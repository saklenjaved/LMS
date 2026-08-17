from django import forms
from django.forms import inlineformset_factory

from apps.accounts.models import User

from .models import Course, QuizQuestion


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "pdf"]


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = [
            "question_text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
        ]


QuizQuestionFormSet = inlineformset_factory(
    Course,
    QuizQuestion,
    form=QuizQuestionForm,
    extra=5,
    min_num=4,
    max_num=5,
    validate_min=True,
    validate_max=True,
    can_delete=True,
)


class AssignCourseForm(forms.Form):
    employees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE),
        widget=forms.CheckboxSelectMultiple,
    )


class BulkAssignForm(forms.Form):
    course = forms.ModelChoiceField(queryset=Course.objects.all())
    employees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role=User.Role.EMPLOYEE),
        widget=forms.CheckboxSelectMultiple,
    )


class QuizAttemptForm(forms.Form):
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions or [])
        for question in self.questions:
            self.fields["q_%s" % question.pk] = forms.ChoiceField(
                label=question.question_text,
                choices=[
                    ("A", question.option_a),
                    ("B", question.option_b),
                    ("C", question.option_c),
                    ("D", question.option_d),
                ],
                widget=forms.RadioSelect,
            )
