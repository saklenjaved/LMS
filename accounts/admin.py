from django.contrib import admin

from .models import User
from .views import notify_employee_approved


class UserAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "role", "status")
    list_filter = ("role", "status")
    actions = ["approve_employees"]

    def approve_employees(self, request, queryset):
        waiting = queryset.filter(role=User.Role.EMPLOYEE, status=User.Status.PENDING)
        count = 0
        for employee in waiting:
            employee.status = User.Status.APPROVED
            employee.save()
            notify_employee_approved(employee)
            count += 1
        self.message_user(request, "Approved %s employee(s)." % count)

    approve_employees.short_description = "Approve selected employees"

    def save_model(self, request, obj, form, change):
        old_status = ""
        if change:
            old = User.objects.get(pk=obj.pk)
            old_status = old.status
        super().save_model(request, obj, form, change)
        became_approved = (
            obj.role == User.Role.EMPLOYEE
            and obj.status == User.Status.APPROVED
            and old_status != User.Status.APPROVED
        )
        if became_approved:
            notify_employee_approved(obj)


admin.site.register(User, UserAdmin)
