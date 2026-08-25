import django.db.models.deletion
from django.db import migrations, models


def copy_old_options(apps, schema_editor):
    QuizQuestion = apps.get_model("courses", "QuizQuestion")
    QuizOption = apps.get_model("courses", "QuizOption")
    for q in QuizQuestion.objects.all():
        pairs = [
            ("A", q.option_a),
            ("B", q.option_b),
            ("C", q.option_c),
            ("D", q.option_d),
        ]
        for letter, text in pairs:
            QuizOption.objects.create(
                question=q,
                option_text=text,
                is_correct=q.correct_option == letter,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_enrollment_quiz_correct_enrollment_quiz_wrong"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quizquestion",
            name="question_text",
            field=models.TextField(),
        ),
        migrations.CreateModel(
            name="QuizOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("option_text", models.CharField(max_length=255)),
                ("is_correct", models.BooleanField(default=False)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="courses.quizquestion",
                    ),
                ),
            ],
        ),
        migrations.RunPython(copy_old_options, migrations.RunPython.noop),
        migrations.RemoveField(model_name="quizquestion", name="option_a"),
        migrations.RemoveField(model_name="quizquestion", name="option_b"),
        migrations.RemoveField(model_name="quizquestion", name="option_c"),
        migrations.RemoveField(model_name="quizquestion", name="option_d"),
        migrations.RemoveField(model_name="quizquestion", name="correct_option"),
    ]
