import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.json
from django.db import migrations, models

import netbox_smartlock.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("extras", "0001_initial"),
        ("users", "0015_owner"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("description", models.TextField(blank=True, verbose_name="Mô tả")),
                ("comments", models.TextField(blank=True, default="")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("code", models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ("status", models.CharField(choices=[("active", "Hoạt động"), ("inactive", "Không hoạt động")], default="active", max_length=20)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="users.owner")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"ordering": ("name",), "verbose_name": "Nhóm tài sản", "verbose_name_plural": "Nhóm tài sản"},
        ),
        migrations.CreateModel(
            name="SLRegion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("description", models.CharField(blank=True, max_length=200, default="")),
                ("comments", models.TextField(blank=True, default="")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("code", models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="users.owner")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"ordering": ("name",), "db_table": "netbox_smartlock_region"},
        ),
        migrations.CreateModel(
            name="SLSite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("description", models.CharField(blank=True, max_length=200, default="")),
                ("comments", models.TextField(blank=True, default="")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("code", models.CharField(blank=True, max_length=50)),
                ("region", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sl_sites", to="netbox_smartlock.slregion")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="users.owner")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"ordering": ("region__name", "name"), "db_table": "netbox_smartlock_site"},
        ),
        migrations.CreateModel(
            name="SLLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("description", models.CharField(blank=True, max_length=200, default="")),
                ("comments", models.TextField(blank=True, default="")),
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("code", models.CharField(blank=True, max_length=50)),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sl_locations", to="netbox_smartlock.slsite")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="users.owner")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"ordering": ("site__name", "name"), "db_table": "netbox_smartlock_location"},
        ),
        migrations.CreateModel(
            name="SmartLock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("comments", models.TextField(blank=True, default="")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("status", models.CharField(choices=[("active", "Đang hoạt động"), ("backup", "Dự phòng"), ("maintenance", "Bảo trì"), ("broken", "Hỏng")], default="active", max_length=20)),
                ("description", models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(500)])),
                ("device_type", models.CharField(max_length=100)),
                ("model", models.CharField(blank=True, max_length=100)),
                ("serial", models.CharField(blank=True, max_length=100)),
                ("manufacturer", models.CharField(blank=True, max_length=100)),
                ("setup_date", models.DateField(blank=True, null=True)),
                ("bought_date", models.DateField(blank=True, null=True)),
                ("warranty_period", models.PositiveIntegerField(blank=True, help_text="Đơn vị: tháng", null=True)),
                ("warranty_expiration_date", models.DateField(blank=True, editable=False, null=True)),
                ("attachment", models.FileField(blank=True, null=True, upload_to="smartlocks/attachments/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=("png", "jpg", "jpeg")), netbox_smartlock.models.validate_file_size])),
                ("asset_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="smartlocks", to="netbox_smartlock.assetgroup")),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="smartlocks", to="netbox_smartlock.sllocation")),
                ("region", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="smartlocks", to="netbox_smartlock.slregion")),
                ("site", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="smartlocks", to="netbox_smartlock.slsite")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"ordering": ("-last_updated", "name"), "verbose_name": "Smart Lock", "verbose_name_plural": "Smart Locks"},
        ),
        migrations.AddConstraint(
            model_name="slsite",
            constraint=models.UniqueConstraint(fields=("region", "name"), name="netbox_smartlock_slsite_unique_region_name"),
        ),
        migrations.AddConstraint(
            model_name="sllocation",
            constraint=models.UniqueConstraint(fields=("site", "name"), name="netbox_smartlock_sllocation_unique_site_name"),
        ),
    ]
