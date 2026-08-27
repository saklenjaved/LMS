from django.contrib import admin

from .models import Course, CourseRating, Enrollment, QuizOption, QuizQuestion

admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(QuizQuestion)
admin.site.register(QuizOption)


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "score", "updated_at")
    list_filter = ("score",)
    search_fields = ("enrollment__employee__email", "enrollment__course__title", "comment")
