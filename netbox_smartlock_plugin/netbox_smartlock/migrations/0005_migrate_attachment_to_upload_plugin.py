from pathlib import Path

from django.db import migrations


def migrate_legacy_attachments(apps, schema_editor):
    SmartLock = apps.get_model("netbox_smartlock", "SmartLock")
    UploadedFile = apps.get_model("upload_file_plugin", "UploadedFile")
    ContentType = apps.get_model("contenttypes", "ContentType")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="netbox_smartlock",
        model="smartlock",
    )

    locks = SmartLock.objects.exclude(attachment__isnull=True).exclude(attachment="")
    for lock in locks:
        if not lock.attachment:
            continue

        file_name = Path(lock.attachment.name).name
        UploadedFile.objects.get_or_create(
            model_name="smartlock",
            object_id=lock.pk,
            file=lock.attachment.name,
            defaults={
                "file_name": file_name,
                "content_type": content_type,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("upload_file_plugin", "0003_uploadedfile_file_no_upload_to"),
        ("netbox_smartlock", "0004_smartlock_attachment_image_extensions"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_attachments, migrations.RunPython.noop),
    ]
