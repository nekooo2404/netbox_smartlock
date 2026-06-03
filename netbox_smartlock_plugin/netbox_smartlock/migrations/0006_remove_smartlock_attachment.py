from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0005_migrate_attachment_to_upload_plugin"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="smartlock",
            name="attachment",
        ),
    ]
