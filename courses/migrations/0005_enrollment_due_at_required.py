from django.db import migrations, models
from django.utils import timezone


def fill_missing_due_at(apps, schema_editor):
    Enrollment = apps.get_model("courses", "Enrollment")
    now = timezone.now()
    for enrollment in Enrollment.objects.filter(due_at__isnull=True):
        enrollment.due_at = enrollment.assigned_at or now
        enrollment.save(update_fields=["due_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0004_enrollment_due_at"),
    ]

    operations = [
        migrations.RunPython(fill_missing_due_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="enrollment",
            name="due_at",
            field=models.DateTimeField(),
        ),
    ]
