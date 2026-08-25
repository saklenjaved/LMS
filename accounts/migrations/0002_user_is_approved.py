from django.db import migrations, models


def keep_existing_users_approved(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.update(is_approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_approved",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(keep_existing_users_approved, migrations.RunPython.noop),
    ]
