from django.conf import settings
import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0001_initial"),
        ("extras", "0001_initial"),
        ("netbox_smartlock", "0008_alter_assetgroup_owner"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Request Name")),
                ("expected_date", models.DateField(verbose_name="Expected Date")),
                ("reason", models.TextField(validators=[django.core.validators.MaxLengthValidator(500)], verbose_name="Reason")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("completed", "Completed"),
                        ],
                        default="draft",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "region",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="access_requests",
                        to="dcim.region",
                        verbose_name="Region",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="access_requests",
                        to="dcim.site",
                        verbose_name="Site",
                    ),
                ),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ("-last_updated", "name"),
                "verbose_name": "Access Request",
                "verbose_name_plural": "Access Requests",
            },
        ),
        migrations.CreateModel(
            name="AccessRequestHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("update", "Update"),
                            ("submit", "Submit"),
                            ("accept", "Accept"),
                            ("reject", "Reject"),
                            ("complete", "Complete"),
                        ],
                        max_length=20,
                        verbose_name="Action",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("accepted", "Accepted"),
                            ("rejected", "Rejected"),
                            ("completed", "Completed"),
                        ],
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("time", models.DateTimeField(auto_now_add=True, verbose_name="Time")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Actor",
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="netbox_smartlock.accessrequest",
                        verbose_name="Access Request",
                    ),
                ),
            ],
            options={
                "ordering": ("-time", "-pk"),
                "verbose_name": "Access Request History",
                "verbose_name_plural": "Access Request History",
            },
        ),
        migrations.CreateModel(
            name="AccessRequestPerson",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("identity_code", models.CharField(max_length=12, verbose_name="Identity Code")),
                ("full_name", models.CharField(max_length=50, verbose_name="Full Name")),
                ("organization", models.CharField(max_length=100, verbose_name="Organization")),
                ("title", models.CharField(blank=True, max_length=50, verbose_name="Title")),
                ("phone", models.CharField(blank=True, max_length=10, verbose_name="Phone")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        validators=[django.core.validators.MaxLengthValidator(500)],
                        verbose_name="Description",
                    ),
                ),
                (
                    "verify_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("valid", "Valid"),
                            ("invalid", "Invalid"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Verification Status",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="access_request_persons",
                        to="dcim.location",
                        verbose_name="Location",
                    ),
                ),
                (
                    "request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="persons",
                        to="netbox_smartlock.accessrequest",
                        verbose_name="Access Request",
                    ),
                ),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ("-last_updated", "full_name"),
                "verbose_name": "Access Request Person",
                "verbose_name_plural": "Access Request Persons",
            },
        ),
        migrations.AddConstraint(
            model_name="accessrequestperson",
            constraint=models.UniqueConstraint(
                fields=("request", "identity_code"),
                name="netbox_smartlock_accessrequestperson_unique_request_identity",
            ),
        ),
    ]
