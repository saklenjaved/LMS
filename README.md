# LMS (Django + PostgreSQL)

Simple learning management system for internship: register/login, Admin and Employee roles, PDF courses, quizzes, and printable certificates.

## Create the database in pgAdmin

1. Open pgAdmin and connect to your PostgreSQL server.
2. Open Query Tool on the `postgres` database (not a new empty query without a connection).
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

`createsuperuser` uses **email** (not username). That user is an Admin.

Load dummy employees, courses, quizzes, and enrollments:

```bash
python manage.py seed_demo
```

Demo employee login password for all seeded users: `employee123`

| Email | Name |
| --- | --- |
| ali@example.com | Ali Khan |
| sara@example.com | Sara Ahmed |
| john@example.com | John Smith |
| priya@example.com | Priya Patel |

Courses: Python Basics, Django Fundamentals, PostgreSQL for Developers, Workplace AI Awareness (each with 4–5 MCQs).

Employees can also use **Register** on the site.

## How to demo

1. Login as admin → Add course (PDF + 4–5 MCQs) → Assign to an employee.
2. Login as employee → Open course → Open PDF → Mark as completed → Take quiz.
3. All answers correct → printable HTML certificate. Any wrong answer → no certificate (retry allowed).

## Tests

```bash
python manage.py test
```

Tests use an in-memory SQLite database. The running app uses PostgreSQL.
