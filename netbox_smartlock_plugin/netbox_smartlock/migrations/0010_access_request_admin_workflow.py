from django.db import migrations, models


ACCESS_REQUEST_STATUS_CHOICES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("confirmed", "Confirmed"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("completed", "Completed"),
]

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


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0009_access_requests"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accessrequest",
            name="status",
            field=models.CharField(
                choices=ACCESS_REQUEST_STATUS_CHOICES,
                default="draft",
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="accessrequesthistory",
            name="status",
            field=models.CharField(
                choices=ACCESS_REQUEST_STATUS_CHOICES,
                max_length=20,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="accessrequesthistory",
            name="action",
            field=models.CharField(
                choices=ACCESS_REQUEST_HISTORY_ACTION_CHOICES,
                max_length=20,
                verbose_name="Action",
            ),
        ),
        migrations.AddField(
            model_name="accessrequestperson",
            name="access_status",
            field=models.CharField(
                choices=[
                    ("out", "Out"),
                    ("in", "In"),
                ],
                default="out",
                max_length=10,
                verbose_name="Access Status",
            ),
        ),
    ]
