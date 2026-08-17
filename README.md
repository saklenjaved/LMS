# LMS

Internship learning management system built with **Django 5** and **PostgreSQL**.

Employees register with email, take assigned PDF courses, pass a quiz (every answer must be correct), and receive a printable certificate. Admins manage employees, courses, assignments, quizzes, and results.

Site name: **LMS**. Roles: **Admin** and **Employee** only.

## Features

**Admin**
- Dashboard and reports
- Employees list
- Add, edit, and delete PDF courses
- Assign courses to employees
- Add quiz questions (no question cap; four options plus extras)
- Edit or delete quiz questions from Manage quiz
- View quiz results

**Employee**
- Dashboard, My courses, History
- Open the course PDF, then mark the course complete
- Take the quiz (retry if they fail)
- First passing attempt shows a certificate popup
- Portrait certificate page with Print and Back

Login uses **email**, not username.

## Create the database in pgAdmin

1. Open pgAdmin and connect to your PostgreSQL server.
2. Open Query Tool on the `postgres` database.
3. Run:

```sql
CREATE DATABASE lms_db;
```

4. Copy `.env.example` to `.env` and set `DB_USER` / `DB_PASSWORD` to your local Postgres login (often user `postgres`).

## Run the app

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

`createsuperuser` asks for **email**. That account is an Admin.

## Demo data

```bash
python manage.py seed_demo
```

Password for every seeded employee: `employee123`

| Email | Name |
| --- | --- |
| ali@example.com | Ali Khan |
| sara@example.com | Sara Ahmed |
| john@example.com | John Smith |
| priya@example.com | Priya Patel |

Courses: Python Basics, Django Fundamentals, PostgreSQL for Developers, Workplace AI Awareness.

You can also use **Register** on the site to create an employee.

## How to demo

1. Login as admin → **Manage courses** → add a course (save first) → add quiz questions → **Course assignment**.
2. Login as employee → open the course → Open PDF → Mark as completed → Take quiz.
3. All answers correct → review page and a one-time **Show certificate** popup → Print or Back.
4. Any wrong answer → no certificate; the employee can retake the quiz.

## Project layout

- `apps/accounts` — users (email login, Admin / Employee)
- `apps/courses` — courses, quizzes, enrollments, certificates
- `apps/core` — home, dashboard, reports, demo seed
- `config/` — Django settings
- `templates/` — HTML layouts and pages

## Tests

```bash
python manage.py test
```

Tests use in-memory SQLite. The running app uses PostgreSQL.
