# LMS v1 Scope

## Confirmed in v1

- Register, login, logout (email + password)
- Roles: **Admin**, **Employee**
- Courses created by admin: title, description, PDF
- Admin assigns courses to employees
- Employees learn assigned courses (read PDF) and mark complete
- After complete: 4–5 MCQ quiz from course questions
- **Pass = all answers correct** → printable HTML certificate
- Fail → no certificate; employee may retake the quiz

## Out of v1

- Extra roles, REST API, lessons, assignments, video, PDF certificates

## Tech

- Django 5, PostgreSQL, server-rendered templates
- `AUTH_USER_MODEL = accounts.User`, `USERNAME_FIELD = email`

## PostgreSQL (pgAdmin)

Run on the `postgres` database in Query Tool:

```sql
CREATE DATABASE lms_db;
```

Then set `.env` (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) and run migrations.

## Build phases

1. Project scaffold
2. PostgreSQL + migrations
3. Auth and roles
4. Courses, PDF, assignment
5. Quiz and certificate
6. Templates, README, tests
