from django.db import migrations


def grant_admin_staff(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="admin").update(is_staff=True, is_superuser=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_set_site"),
    ]

    operations = [
        migrations.RunPython(grant_admin_staff, migrations.RunPython.noop),
    ]
