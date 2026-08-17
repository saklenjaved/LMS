---
name: lms-add-feature
description: Adds a small LMS feature with model, simple form, function view, url, and template. Use when adding courses, quiz, employees, reports, or any new LMS page.
---

# Add an LMS feature

Keep it basic. Do not introduce new apps unless the user asks.

1. Add fields on an existing model in `apps/courses` or `apps/accounts` if possible.
2. `python manage.py makemigrations` then `migrate`.
3. Simple `ModelForm` with `Meta.fields`.
4. Short function view. Admin pages: check `request.user.is_admin`. Employee pages: check `request.user.is_employee`.
5. Add a `path()` in that app's `urls.py`.
6. Simple template extending `layouts/admin.html` or `layouts/employee.html`.
7. `admin.site.register` if a new model was added.

Site name stays **LMS**. No extra roles. No REST API.
