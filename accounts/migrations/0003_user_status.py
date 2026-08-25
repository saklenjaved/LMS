from django.db import migrations, models


def copy_approval_to_status(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_approved=True).update(status="approved")
    User.objects.filter(is_approved=False).update(status="pending")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_is_approved"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("blocked", "Blocked"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.RunPython(copy_approval_to_status, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="is_approved",
        ),
    ]
