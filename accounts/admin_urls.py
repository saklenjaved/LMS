from django.urls import path

from . import views

urlpatterns = [
    path("", views.employee_list, name="employees"),
    path("filter/", views.employee_filter, name="employee_filter"),
    path("<int:pk>/edit/", views.edit_employee, name="edit_employee"),
    path("<int:pk>/approve/", views.approve_employee, name="approve_employee"),
    path("<int:pk>/block/", views.block_employee, name="block_employee"),
]
