from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from apps.core.mixins import AdminRequiredMixin, EmployeeRequiredMixin, NavActiveMixin

from .forms import AssignCourseForm, BulkAssignForm, CourseForm, QuizAttemptForm, QuizQuestionFormSet
from .models import Course, Enrollment


class CourseListView(NavActiveMixin, AdminRequiredMixin, ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    nav_active = "courses"


class CourseCreateView(NavActiveMixin, AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses:list")
    nav_active = "courses"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = QuizQuestionFormSet(self.request.POST)
        else:
            context["formset"] = QuizQuestionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        form.instance.created_by = self.request.user
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Course created.")
            return redirect(self.success_url)
        return self.form_invalid(form)


class CourseUpdateView(NavActiveMixin, AdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses:list")
    nav_active = "courses"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = QuizQuestionFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = QuizQuestionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Course updated.")
            return redirect(self.success_url)
        return self.form_invalid(form)


class CourseDeleteView(NavActiveMixin, AdminRequiredMixin, DeleteView):
    model = Course
    template_name = "courses/course_confirm_delete.html"
    success_url = reverse_lazy("courses:list")
    nav_active = "courses"


class EnrollmentListView(NavActiveMixin, AdminRequiredMixin, ListView):
    model = Enrollment
    template_name = "courses/enrollment_list.html"
    context_object_name = "enrollments"
    nav_active = "employee_courses"

    def get_queryset(self):
        return Enrollment.objects.select_related("employee", "course").order_by(
            "-assigned_at"
        )


class AssignCourseView(NavActiveMixin, AdminRequiredMixin, FormView):
    template_name = "courses/assign_course.html"
    form_class = AssignCourseForm
    nav_active = "assignments"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context

    def form_valid(self, form):
        created = 0
        for employee in form.cleaned_data["employees"]:
            _, was_created = Enrollment.objects.get_or_create(
                employee=employee,
                course=self.course,
            )
            if was_created:
                created += 1
        messages.success(self.request, f"Assigned to {created} employee(s).")
        return redirect("courses:assignments")


class AssignmentHubView(NavActiveMixin, AdminRequiredMixin, FormView):
    template_name = "courses/assignment_hub.html"
    form_class = BulkAssignForm
    nav_active = "assignments"

    def form_valid(self, form):
        course = form.cleaned_data["course"]
        created = 0
        for employee in form.cleaned_data["employees"]:
            _, was_created = Enrollment.objects.get_or_create(
                employee=employee,
                course=course,
            )
            if was_created:
                created += 1
        messages.success(self.request, f"Assigned {course.title} to {created} employee(s).")
        return redirect("courses:assignments")


class QuizResultListView(NavActiveMixin, AdminRequiredMixin, ListView):
    template_name = "courses/quiz_results.html"
    context_object_name = "enrollments"
    nav_active = "quiz_results"

    def get_queryset(self):
        return (
            Enrollment.objects.filter(
                status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED]
            )
            .select_related("employee", "course")
            .order_by("-quiz_taken_at")
        )


class QuizManageListView(NavActiveMixin, AdminRequiredMixin, ListView):
    model = Course
    template_name = "courses/quiz_manage_list.html"
    context_object_name = "courses"
    nav_active = "quizzes"


class QuizEditView(NavActiveMixin, AdminRequiredMixin, UpdateView):
    model = Course
    fields = []
    template_name = "courses/quiz_edit.html"
    success_url = reverse_lazy("courses:quizzes")
    nav_active = "quizzes"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["formset"] = QuizQuestionFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = QuizQuestionFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]
        if formset.is_valid():
            formset.instance = self.object
            formset.save()
            messages.success(self.request, "Quiz updated.")
            return redirect(self.success_url)
        return self.form_invalid(form)


class MyCourseListView(NavActiveMixin, EmployeeRequiredMixin, ListView):
    template_name = "courses/my_courses.html"
    context_object_name = "enrollments"
    nav_active = "my_courses"

    def get_queryset(self):
        return (
            Enrollment.objects.filter(
                employee=self.request.user,
                status__in=[Enrollment.Status.ASSIGNED, Enrollment.Status.COMPLETED],
            )
            .select_related("course")
            .order_by("-assigned_at")
        )


class HistoryListView(NavActiveMixin, EmployeeRequiredMixin, ListView):
    template_name = "courses/history.html"
    context_object_name = "enrollments"
    nav_active = "history"

    def get_queryset(self):
        return (
            Enrollment.objects.filter(
                employee=self.request.user,
                status__in=[Enrollment.Status.PASSED, Enrollment.Status.FAILED],
            )
            .select_related("course")
            .order_by("-quiz_taken_at")
        )


class MyCourseDetailView(NavActiveMixin, EmployeeRequiredMixin, DetailView):
    template_name = "courses/my_course_detail.html"
    context_object_name = "enrollment"
    nav_active = "my_courses"

    def get_queryset(self):
        return Enrollment.objects.filter(employee=self.request.user).select_related(
            "course"
        )


class MarkCompleteView(EmployeeRequiredMixin, View):
    def post(self, request, pk):
        enrollment = get_object_or_404(
            Enrollment, pk=pk, employee=request.user
        )
        if enrollment.status == Enrollment.Status.ASSIGNED:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completed_at = timezone.now()
            enrollment.save(update_fields=["status", "completed_at"])
            messages.success(request, "Course marked complete. You can take the quiz.")
        return redirect("courses:my_detail", pk=enrollment.pk)


class QuizView(NavActiveMixin, EmployeeRequiredMixin, FormView):
    template_name = "courses/quiz.html"
    nav_active = "my_courses"

    def dispatch(self, request, *args, **kwargs):
        self.enrollment = get_object_or_404(
            Enrollment, pk=kwargs["pk"], employee=request.user
        )
        if self.enrollment.status == Enrollment.Status.ASSIGNED:
            messages.warning(request, "Mark the course as completed before the quiz.")
            return redirect("courses:my_detail", pk=self.enrollment.pk)
        self.questions = list(self.enrollment.course.questions.all())
        if len(self.questions) < 4:
            messages.error(request, "This course has no quiz yet.")
            return redirect("courses:my_detail", pk=self.enrollment.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["questions"] = self.questions
        return kwargs

    def get_form_class(self):
        return QuizAttemptForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enrollment"] = self.enrollment
        return context

    def form_valid(self, form):
        correct = 0
        wrong = 0
        rows = []
        for question in self.questions:
            chosen = form.cleaned_data.get("q_%s" % question.pk)
            options = {
                "A": question.option_a,
                "B": question.option_b,
                "C": question.option_c,
                "D": question.option_d,
            }
            ok = chosen == question.correct_option
            if ok:
                correct += 1
            else:
                wrong += 1
            rows.append(
                {
                    "text": question.question_text,
                    "ok": ok,
                    "chosen_text": options.get(chosen, ""),
                    "correct_text": options.get(question.correct_option, ""),
                }
            )
        self.enrollment.quiz_taken_at = timezone.now()
        self.enrollment.quiz_correct = correct
        self.enrollment.quiz_wrong = wrong
        if wrong == 0:
            self.enrollment.status = Enrollment.Status.PASSED
        else:
            self.enrollment.status = Enrollment.Status.FAILED
        self.enrollment.save()
        self.request.session["quiz_review_%s" % self.enrollment.pk] = {"rows": rows}
        return redirect("courses:quiz_review", pk=self.enrollment.pk)


@login_required
def quiz_review(request, pk):
    if request.user.role != "employee":
        return redirect("core:dashboard")
    enrollment = get_object_or_404(Enrollment, pk=pk, employee=request.user)
    if enrollment.status not in (Enrollment.Status.PASSED, Enrollment.Status.FAILED):
        return redirect("courses:my_detail", pk=pk)
    rows = request.session.get("quiz_review_%s" % pk, {}).get("rows", [])
    return render(
        request,
        "courses/quiz_review.html",
        {
            "enrollment": enrollment,
            "rows": rows,
            "nav_active": "history",
        },
    )


class CertificateView(NavActiveMixin, EmployeeRequiredMixin, DetailView):
    template_name = "courses/certificate.html"
    context_object_name = "enrollment"

    def get_queryset(self):
        return Enrollment.objects.filter(
            employee=self.request.user, status=Enrollment.Status.PASSED
        ).select_related("course", "employee")

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            messages.error(request, "Certificate is only available after a passing quiz.")
            return redirect("courses:my_list")
