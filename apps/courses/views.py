from django.contrib import messages
from django.contrib.auth.decorators import login_required
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

from apps.accounts.emails import notify_course_assigned
from apps.core.mixins import AdminRequiredMixin, EmployeeRequiredMixin, NavActiveMixin

from .forms import AssignCourseForm, BulkAssignForm, CourseForm, QuizAttemptForm
from .models import Course, Enrollment, QuizOption, QuizQuestion


class CourseListView(NavActiveMixin, AdminRequiredMixin, ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    nav_active = "courses"


class CourseCreateView(NavActiveMixin, AdminRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    nav_active = "courses"

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        self.object = form.save()
        messages.success(self.request, "Course saved. Now add a quiz.")
        return redirect("courses:quiz_add", pk=self.object.pk)


class CourseUpdateView(NavActiveMixin, AdminRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses:list")
    nav_active = "courses"

    def form_valid(self, form):
        messages.success(self.request, "Course updated.")
        return super().form_valid(form)


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
        due_at = form.cleaned_data.get("due_at")
        for employee in form.cleaned_data["employees"]:
            enrollment, was_created = Enrollment.objects.get_or_create(
                employee=employee,
                course=self.course,
                defaults={"due_at": due_at},
            )
            if was_created:
                created += 1
                notify_course_assigned(employee, self.course, enrollment)
        messages.success(self.request, f"Assigned to {created} employee(s).")
        return redirect("courses:assignments")


class AssignmentHubView(NavActiveMixin, AdminRequiredMixin, FormView):
    template_name = "courses/assignment_hub.html"
    form_class = BulkAssignForm
    nav_active = "assignments"

    def form_valid(self, form):
        course = form.cleaned_data["course"]
        due_at = form.cleaned_data.get("due_at")
        created = 0
        for employee in form.cleaned_data["employees"]:
            enrollment, was_created = Enrollment.objects.get_or_create(
                employee=employee,
                course=course,
                defaults={"due_at": due_at},
            )
            if was_created:
                created += 1
                notify_course_assigned(employee, course, enrollment)
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


def save_options(request, question):
    try:
        extra = int(request.POST.get("extra", 0))
    except (TypeError, ValueError):
        extra = 0
    if extra < 0:
        extra = 0
    total = 4 + extra
    try:
        correct = int(request.POST.get("correct", 1))
    except (TypeError, ValueError):
        correct = 1
    n = 1
    while n <= total:
        QuizOption.objects.create(
            question=question,
            option_text=request.POST.get("option_%s" % n, ""),
            is_correct=n == correct,
        )
        n += 1


def quiz_questions(request, pk):
    if not request.user.is_authenticated or request.user.role != "admin":
        return redirect("core:dashboard")
    course = get_object_or_404(Course, pk=pk)
    return render(
        request,
        "courses/quiz_questions.html",
        {
            "course": course,
            "questions": course.questions.all(),
            "nav_active": "quizzes",
        },
    )


def quiz_add(request, pk):
    if not request.user.is_authenticated or request.user.role != "admin":
        return redirect("core:dashboard")
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        text = request.POST.get("question_text", "").strip()
        if not text:
            messages.error(request, "Please write the question.")
            return render(
                request,
                "courses/quiz_add.html",
                {"course": course, "nav_active": "quizzes"},
            )
        question = QuizQuestion.objects.create(course=course, question_text=text)
        save_options(request, question)
        messages.success(request, "Question saved. Add another if you want.")
        return redirect("courses:quiz_questions", pk=course.pk)
    return render(
        request,
        "courses/quiz_add.html",
        {"course": course, "nav_active": "quizzes"},
    )


def quiz_edit(request, pk):
    if not request.user.is_authenticated or request.user.role != "admin":
        return redirect("core:dashboard")
    question = get_object_or_404(QuizQuestion, pk=pk)
    options = list(question.options.order_by("id"))
    texts = []
    for option in options:
        texts.append(option.option_text)
    while len(texts) < 4:
        texts.append("")
    extra_texts = texts[4:]
    correct = 1
    i = 1
    for option in options:
        if option.is_correct:
            correct = i
            break
        i += 1
    if request.method == "POST":
        text = request.POST.get("question_text", "").strip()
        if not text:
            messages.error(request, "Please write the question.")
        else:
            question.question_text = text
            question.save()
            question.options.all().delete()
            save_options(request, question)
            messages.success(request, "Question updated.")
            return redirect("courses:quiz_questions", pk=question.course_id)
    return render(
        request,
        "courses/quiz_edit.html",
        {
            "question": question,
            "course": question.course,
            "first_four": texts[:4],
            "extra_texts": extra_texts,
            "extra": len(extra_texts),
            "correct": correct,
            "option_total": len(texts),
            "correct_choices": range(1, len(texts) + 1),
            "nav_active": "quizzes",
        },
    )


def quiz_delete_question(request, pk):
    if not request.user.is_authenticated or request.user.role != "admin":
        return redirect("core:dashboard")
    question = get_object_or_404(QuizQuestion, pk=pk)
    course = question.course
    if request.method == "POST":
        question.delete()
        messages.success(request, "Question deleted.")
        return redirect("courses:quiz_questions", pk=course.pk)
    return render(
        request,
        "courses/quiz_question_confirm_delete.html",
        {"question": question, "course": course, "nav_active": "quizzes"},
    )


def quiz_delete(request, pk):
    if not request.user.is_authenticated or request.user.role != "admin":
        return redirect("core:dashboard")
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        course.questions.all().delete()
        messages.success(request, "Quiz deleted.")
        return redirect("courses:quizzes")
    return render(
        request,
        "courses/quiz_confirm_delete.html",
        {"course": course, "nav_active": "quizzes"},
    )


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
        self.questions = list(self.enrollment.course.questions.prefetch_related("options"))
        if len(self.questions) == 0:
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
        score = 0
        wrong = 0
        rows = []
        for question in self.questions:
            chosen = form.cleaned_data.get("q_%s" % question.pk)
            right = question.options.filter(is_correct=True).first()
            picked = question.options.filter(pk=chosen).first()
            ok = right is not None and str(right.pk) == str(chosen)
            if ok:
                score += 1
            else:
                wrong += 1
            rows.append(
                {
                    "text": question.question_text,
                    "ok": ok,
                    "chosen_text": picked.option_text if picked else "",
                    "correct_text": right.option_text if right else "",
                }
            )
        self.enrollment.quiz_taken_at = timezone.now()
        self.enrollment.quiz_correct = score
        self.enrollment.quiz_wrong = wrong
        already_passed = self.enrollment.status == Enrollment.Status.PASSED
        if wrong == 0:
            self.enrollment.status = Enrollment.Status.PASSED
            if not already_passed:
                self.request.session["show_cert_popup"] = self.enrollment.pk
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
    show_cert_popup = False
    if request.session.get("show_cert_popup") == enrollment.pk:
        show_cert_popup = True
        del request.session["show_cert_popup"]
    return render(
        request,
        "courses/quiz_review.html",
        {
            "enrollment": enrollment,
            "rows": rows,
            "show_cert_popup": show_cert_popup,
            "nav_active": "history",
        },
    )


@login_required
def certificate(request, pk):
    if request.user.role != "employee":
        return redirect("core:dashboard")
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("course", "employee"),
        pk=pk,
        employee=request.user,
    )
    if enrollment.status != Enrollment.Status.PASSED:
        messages.error(request, "Certificate is only available after a passing quiz.")
        return redirect("courses:my_list")
    return render(
        request,
        "courses/certificate.html",
        {"enrollment": enrollment},
    )


@login_required
def certificate_pdf(request, pk):
    if request.user.role != "employee":
        return redirect("core:dashboard")
    enrollment = get_object_or_404(
        Enrollment.objects.select_related("course", "employee"),
        pk=pk,
        employee=request.user,
    )
    if enrollment.status != Enrollment.Status.PASSED:
        messages.error(request, "Certificate is only available after a passing quiz.")
        return redirect("courses:my_list")
    from django.http import FileResponse

    from .certificate_pdf import build_certificate_pdf

    buffer = build_certificate_pdf(enrollment)
    filename = "certificate-%s.pdf" % enrollment.pk
    return FileResponse(buffer, as_attachment=True, filename=filename)
