from django.db import migrations


def backfill_created_by(apps, schema_editor):
    AccessRequest = apps.get_model("netbox_smartlock", "AccessRequest")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ObjectChange = apps.get_model("core", "ObjectChange")

    try:
        content_type = ContentType.objects.get(app_label="netbox_smartlock", model="accessrequest")
    except ContentType.DoesNotExist:
        return

    for access_request in AccessRequest.objects.filter(created_by__isnull=True).only("pk"):
        change = (
            ObjectChange.objects.filter(
                changed_object_type=content_type,
                changed_object_id=access_request.pk,
                action="create",
                user__isnull=False,
            )
            .order_by("time")
            .only("user_id")
            .first()
        )
        if change:
            AccessRequest.objects.filter(pk=access_request.pk, created_by__isnull=True).update(created_by_id=change.user_id)


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("core", "0024_job_notifications"),
        ("netbox_smartlock", "0011_accessrequest_created_by"),
    ]

    operations = [
        migrations.RunPython(backfill_created_by, migrations.RunPython.noop),
    ]
