from django.db import migrations, models


ACCESS_REQUEST_HISTORY_ACTION_CHOICES = [
    ("create", "Create"),
    ("update", "Update"),
    ("submit", "Submit"),
    ("confirm", "Confirm"),
    ("accept", "Accept"),
    ("reject", "Reject"),
    ("complete", "Complete"),
    ("verify_valid", "Verify Valid"),
    ("verify_invalid", "Verify Invalid"),
    ("in", "In"),
    ("out", "Out"),
]

LEGACY_IN_ACTION = "_".join(("check", "in"))
LEGACY_OUT_ACTION = "_".join(("check", "out"))
LEGACY_IN_DESCRIPTION_PREFIX = " ".join(("Checked", "in", ""))
LEGACY_OUT_DESCRIPTION_PREFIX = " ".join(("Checked", "out", ""))
IN_DESCRIPTION_PREFIX = "Out -> In: "
OUT_DESCRIPTION_PREFIX = "In -> Out: "


def replace_description_prefix(value, old_prefix, new_prefix):
    if not value.startswith(old_prefix):
        return value
    return f"{new_prefix}{value[len(old_prefix):]}"


def rename_history_actions_forward(apps, schema_editor):
    AccessRequestHistory = apps.get_model("netbox_smartlock", "AccessRequestHistory")
    for history in AccessRequestHistory.objects.filter(action=LEGACY_IN_ACTION, description__startswith=LEGACY_IN_DESCRIPTION_PREFIX):
        history.description = replace_description_prefix(
            history.description,
            LEGACY_IN_DESCRIPTION_PREFIX,
            IN_DESCRIPTION_PREFIX,
        )
        history.save(update_fields=("description",))
    for history in AccessRequestHistory.objects.filter(action=LEGACY_OUT_ACTION, description__startswith=LEGACY_OUT_DESCRIPTION_PREFIX):
        history.description = replace_description_prefix(
            history.description,
            LEGACY_OUT_DESCRIPTION_PREFIX,
            OUT_DESCRIPTION_PREFIX,
        )
        history.save(update_fields=("description",))
    AccessRequestHistory.objects.filter(action=LEGACY_IN_ACTION).update(action="in")
    AccessRequestHistory.objects.filter(action=LEGACY_OUT_ACTION).update(action="out")


def rename_history_actions_reverse(apps, schema_editor):
    AccessRequestHistory = apps.get_model("netbox_smartlock", "AccessRequestHistory")
    for history in AccessRequestHistory.objects.filter(action="in", description__startswith=IN_DESCRIPTION_PREFIX):
        history.description = replace_description_prefix(
            history.description,
            IN_DESCRIPTION_PREFIX,
            LEGACY_IN_DESCRIPTION_PREFIX,
        )
        history.save(update_fields=("description",))
    for history in AccessRequestHistory.objects.filter(action="out", description__startswith=OUT_DESCRIPTION_PREFIX):
        history.description = replace_description_prefix(
            history.description,
            OUT_DESCRIPTION_PREFIX,
            LEGACY_OUT_DESCRIPTION_PREFIX,
        )
        history.save(update_fields=("description",))
    AccessRequestHistory.objects.filter(action="in").update(action=LEGACY_IN_ACTION)
    AccessRequestHistory.objects.filter(action="out").update(action=LEGACY_OUT_ACTION)


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0012_backfill_accessrequest_created_by"),
    ]

    operations = [
        migrations.RunPython(rename_history_actions_forward, rename_history_actions_reverse),
        migrations.AlterField(
            model_name="accessrequesthistory",
            name="action",
            field=models.CharField(
                choices=ACCESS_REQUEST_HISTORY_ACTION_CHOICES,
                max_length=20,
                verbose_name="Action",
            ),
        ),
    ]
