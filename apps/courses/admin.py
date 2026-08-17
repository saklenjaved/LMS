from django.contrib import admin

from .models import Course, Enrollment, QuizOption, QuizQuestion

admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(QuizQuestion)
admin.site.register(QuizOption)
