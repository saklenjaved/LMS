from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.courses.models import Course, Enrollment, QuizOption, QuizQuestion

DEMO_PASSWORD = "employee123"

EMPLOYEES = [
    ("ali@example.com", "Ali", "Khan"),
    ("sara@example.com", "Sara", "Ahmed"),
    ("john@example.com", "John", "Smith"),
    ("priya@example.com", "Priya", "Patel"),
]

COURSES = [
    {
        "title": "Python Basics",
        "description": "Variables, data types, and simple control flow for new developers.",
        "questions": [
            (
                "Which keyword defines a function in Python?",
                "func",
                "def",
                "function",
                "lambda",
                "B",
            ),
            (
                "What is the output type of 3 / 2 in Python 3?",
                "int",
                "str",
                "float",
                "bool",
                "C",
            ),
            (
                "Which collection is ordered and changeable?",
                "tuple",
                "set",
                "list",
                "frozenset",
                "C",
            ),
            (
                "How do you start a comment?",
                "//",
                "/*",
                "#",
                "--",
                "C",
            ),
        ],
    },
    {
        "title": "Django Fundamentals",
        "description": "Models, views, templates, and how a Django request is handled.",
        "questions": [
            (
                "What does MTV stand for in Django?",
                "Model Template View",
                "Model Table View",
                "Main Template Variable",
                "Module Test View",
                "A",
            ),
            (
                "Which file usually maps URLs to views?",
                "models.py",
                "urls.py",
                "admin.py",
                "apps.py",
                "B",
            ),
            (
                "Which command applies database migrations?",
                "python manage.py runserver",
                "python manage.py startapp",
                "python manage.py migrate",
                "python manage.py shell",
                "C",
            ),
            (
                "AUTH_USER_MODEL is set in which file?",
                "urls.py",
                "settings.py",
                "wsgi.py",
                "manage.py",
                "B",
            ),
            (
                "A FileField stores uploaded files where by default?",
                "In the database as text",
                "On disk (MEDIA_ROOT)",
                "In Redis",
                "In cookies",
                "B",
            ),
        ],
    },
    {
        "title": "PostgreSQL for Developers",
        "description": "Tables, primary keys, and simple SQL used with Django.",
        "questions": [
            (
                "Which statement creates a new table?",
                "MAKE TABLE",
                "CREATE TABLE",
                "NEW TABLE",
                "ADD TABLE",
                "B",
            ),
            (
                "PRIMARY KEY values must be:",
                "Duplicated",
                "Optional",
                "Unique",
                "Always text",
                "C",
            ),
            (
                "Which type stores true/false?",
                "VARCHAR",
                "INTEGER",
                "BOOLEAN",
                "DATE",
                "C",
            ),
            (
                "Django talks to PostgreSQL using which setting key?",
                "CACHES",
                "DATABASES",
                "STATICFILES",
                "TEMPLATES",
                "B",
            ),
        ],
    },
    {
        "title": "Workplace AI Awareness",
        "description": "Using AI tools at work: accuracy, privacy, and responsible use.",
        "questions": [
            (
                "Before sending company data to an AI tool you should:",
                "Always paste the full database",
                "Check company policy and privacy rules",
                "Disable passwords",
                "Share your login",
                "B",
            ),
            (
                "AI-generated answers can be:",
                "Always 100% correct",
                "Wrong or outdated",
                "Legal advice automatically",
                "A replacement for backups",
                "B",
            ),
            (
                "A good use of AI at work is:",
                "Hiding mistakes from your manager",
                "Drafting a first version you then review",
                "Skipping all testing",
                "Publishing secrets",
                "B",
            ),
            (
                "If an AI result looks unsure you should:",
                "Ship it immediately",
                "Verify with docs or a teammate",
                "Delete the project",
                "Ignore the task",
                "B",
            ),
            (
                "Who is responsible for work you submit after using AI?",
                "Only the AI vendor",
                "Nobody",
                "You (the employee)",
                "A random internet user",
                "C",
            ),
        ],
    },
]


def _pdf_bytes(title: str) -> bytes:
    text = title.replace("(", " ").replace(")", " ")[:60]
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode("latin-1", "replace")
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length "
        + str(len(stream)).encode()
        + b">>stream\n"
        + stream
        + b"\nendstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"xref\n0 6\n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n0\n"
        b"%%EOF\n"
    )


class Command(BaseCommand):
    help = "Load demo employees, courses, quizzes, and enrollments."

    def handle(self, *args, **options):
        admin = User.objects.filter(role=User.Role.ADMIN).first()
        if admin is None:
            admin = User.objects.create_superuser(
                email="admin@example.com",
                password="admin12345",
                first_name="Admin",
                last_name="User",
            )
            self.stdout.write(self.style.SUCCESS(f"Created admin {admin.email} / admin12345"))
        else:
            self.stdout.write(f"Using existing admin {admin.email}")

        employees = []
        for email, first, last in EMPLOYEES:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.EMPLOYEE,
                    "status": User.Status.APPROVED,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created employee {email} / {DEMO_PASSWORD}"))
            else:
                self.stdout.write(f"Employee already exists: {email}")
            employees.append(user)

        courses = []
        for spec in COURSES:
            course, created = Course.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "description": spec["description"],
                    "created_by": admin,
                },
            )
            if created or not course.pdf:
                course.pdf.save(
                    f"{spec['title'].lower().replace(' ', '_')}.pdf",
                    ContentFile(_pdf_bytes(spec["title"])),
                    save=True,
                )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created course: {course.title}"))
            else:
                self.stdout.write(f"Course already exists: {course.title}")

            if course.questions.count() == 0:
                for text, a, b, c, d, correct in spec["questions"]:
                    question = QuizQuestion.objects.create(
                        course=course,
                        question_text=text,
                    )
                    options = [a, b, c, d]
                    letters = {"A": 0, "B": 1, "C": 2, "D": 3}
                    correct_index = letters[correct]
                    i = 0
                    for opt in options:
                        QuizOption.objects.create(
                            question=question,
                            option_text=opt,
                            is_correct=i == correct_index,
                        )
                        i += 1
                self.stdout.write(f"  Added {len(spec['questions'])} quiz questions")
            courses.append(course)

        # Assign a mix of courses so every employee has work to do.
        assignments = [
            (employees[0], courses[0]),
            (employees[0], courses[1]),
            (employees[1], courses[1]),
            (employees[1], courses[2]),
            (employees[2], courses[0]),
            (employees[2], courses[3]),
            (employees[3], courses[2]),
            (employees[3], courses[3]),
        ]
        created_enrollments = 0
        for employee, course in assignments:
            _, was_created = Enrollment.objects.get_or_create(
                employee=employee,
                course=course,
            )
            if was_created:
                created_enrollments += 1
        self.stdout.write(self.style.SUCCESS(f"Enrollments created: {created_enrollments}"))
        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
