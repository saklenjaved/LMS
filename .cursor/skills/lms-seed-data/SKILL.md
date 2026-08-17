---
name: lms-seed-data
description: Loads or extends demo LMS data (employees, courses, quizzes, enrollments). Use when the user asks for dummy data, seed, fixtures, or sample users.
---

# Seed demo data

Use the existing command:

```bash
python manage.py seed_demo
```

File: `apps/core/management/commands/seed_demo.py`

- Keep lists of tuples/dicts at the top of the file.
- `get_or_create` so it is safe to run twice.
- Employee password: `employee123`
- Do not add factories or fake libraries.
