import calendar
import django.core.validators
import django.db.models.deletion
import taggit.managers
import utilities.json

from datetime import date
from django.core.exceptions import FieldError
from django.db import migrations, models
from django.utils.dateparse import parse_date


LEGACY_ASSET_GROUP_FIELD = "smartlock_asset_group"
LEGACY_ASSET_STATUS_FIELD = "smartlock_asset_status"
LEGACY_ASSET_DESCRIPTION_FIELD = "smartlock_asset_description"
LEGACY_SETUP_DATE_FIELD = "smartlock_setup_date"
LEGACY_BOUGHT_DATE_FIELD = "smartlock_bought_date"
LEGACY_WARRANTY_PERIOD_FIELD = "smartlock_warranty_period"
LEGACY_WARRANTY_EXPIRATION_FIELD = "smartlock_warranty_expiration_date"
LEGACY_ASSET_STATUS_CHOICE_SET = "SmartLock DCIM Asset Status"
LEGACY_DEVICE_ASSET_CUSTOM_FIELD_NAMES = (
    LEGACY_ASSET_GROUP_FIELD,
    LEGACY_ASSET_STATUS_FIELD,
    LEGACY_ASSET_DESCRIPTION_FIELD,
    LEGACY_SETUP_DATE_FIELD,
    LEGACY_BOUGHT_DATE_FIELD,
    LEGACY_WARRANTY_PERIOD_FIELD,
    LEGACY_WARRANTY_EXPIRATION_FIELD,
)


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_custom_date(value):
    if not value:
        return None
    if hasattr(value, "isoformat"):
        return value
    return parse_date(str(value))


def parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def normalize_code(value, fallback):
    base = str(value or fallback).strip()[:50]
    return base or str(fallback)[:50]


def unique_asset_code(Asset, source, fallback):
    base = normalize_code(source, fallback)
    code = base
    suffix = 1

    while Asset.objects.filter(code=code).exists():
        suffix_text = f"-{suffix}"
        code = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    return code


def asset_group_pk_from_custom_value(value):
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("id") or value.get("pk") or value.get("value")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def backfill_assets_from_device_custom_fields(apps, schema_editor):
    Asset = apps.get_model("netbox_smartlock", "Asset")
    AssetGroup = apps.get_model("netbox_smartlock", "AssetGroup")
    Device = apps.get_model("dcim", "Device")
    ContentType = apps.get_model("contenttypes", "ContentType")
    UploadedFile = apps.get_model("upload_file_plugin", "UploadedFile")

    asset_content_type, _ = ContentType.objects.get_or_create(
        app_label="netbox_smartlock",
        model="asset",
    )

    for device in Device.objects.all().iterator():
        custom_field_data = getattr(device, "custom_field_data", None) or {}
        asset_group_pk = asset_group_pk_from_custom_value(custom_field_data.get(LEGACY_ASSET_GROUP_FIELD))
        if not asset_group_pk or not AssetGroup.objects.filter(pk=asset_group_pk).exists():
            continue

        status = custom_field_data.get(LEGACY_ASSET_STATUS_FIELD) or "active"
        if status not in {"active", "backup", "maintenance", "broken"}:
            status = "active"

        bought_date = parse_custom_date(custom_field_data.get(LEGACY_BOUGHT_DATE_FIELD))
        warranty_period = parse_positive_int(custom_field_data.get(LEGACY_WARRANTY_PERIOD_FIELD))
        warranty_expiration_date = add_months(bought_date, warranty_period) if bought_date and warranty_period else None
        code = unique_asset_code(Asset, getattr(device, "asset_tag", None), f"device-{device.pk}")

        asset, _ = Asset.objects.get_or_create(
            device_id=device.pk,
            defaults={
                "asset_group_id": asset_group_pk,
                "name": getattr(device, "name", "") or f"Device {device.pk}",
                "code": code,
                "status": status,
                "description": custom_field_data.get(LEGACY_ASSET_DESCRIPTION_FIELD) or "",
                "setup_date": parse_custom_date(custom_field_data.get(LEGACY_SETUP_DATE_FIELD)),
                "bought_date": bought_date,
                "warranty_period": warranty_period,
                "warranty_expiration_date": warranty_expiration_date,
                "comments": "",
            },
        )

        UploadedFile.objects.filter(model_name="device", object_id=device.pk).update(
            content_type=asset_content_type,
            object_id=asset.pk,
            model_name="asset",
        )


def get_object_type(ObjectType, model):
    manager = ObjectType.objects
    if hasattr(manager, "get_for_model"):
        try:
            return manager.get_for_model(model)
        except ObjectType.DoesNotExist:
            return None

    return manager.filter(
        app_label=model._meta.app_label,
        model=model._meta.model_name,
    ).first()


def remove_legacy_device_asset_custom_fields(apps, schema_editor):
    CustomField = apps.get_model("extras", "CustomField")
    CustomFieldChoiceSet = apps.get_model("extras", "CustomFieldChoiceSet")
    ObjectType = apps.get_model("core", "ObjectType")
    Device = apps.get_model("dcim", "Device")

    device_object_type = get_object_type(ObjectType, Device)
    if device_object_type is None:
        return

    for custom_field in CustomField.objects.filter(name__in=LEGACY_DEVICE_ASSET_CUSTOM_FIELD_NAMES):
        if hasattr(custom_field, "object_types"):
            custom_field.object_types.remove(device_object_type)
            if not custom_field.object_types.exists():
                custom_field.delete()
        elif hasattr(custom_field, "content_types"):
            custom_field.content_types.remove(device_object_type)
            if not custom_field.content_types.exists():
                custom_field.delete()

    try:
        choice_set_is_unused = not CustomField.objects.filter(
            choice_set__name=LEGACY_ASSET_STATUS_CHOICE_SET,
        ).exists()
    except FieldError:
        choice_set_is_unused = True

    if choice_set_is_unused:
        CustomFieldChoiceSet.objects.filter(name=LEGACY_ASSET_STATUS_CHOICE_SET).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("dcim", "0001_initial"),
        ("extras", "0001_initial"),
        ("netbox_smartlock", "0015_assetgroup_code_visualization_ordering"),
        ("upload_file_plugin", "0003_uploadedfile_file_no_upload_to"),
    ]

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="Code")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("backup", "Backup"),
                            ("maintenance", "Maintenance"),
                            ("broken", "Broken"),
                        ],
                        default="active",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        validators=[django.core.validators.MaxLengthValidator(500)],
                        verbose_name="Description",
                    ),
                ),
                ("setup_date", models.DateField(blank=True, null=True, verbose_name="Setup Date")),
                ("bought_date", models.DateField(blank=True, null=True, verbose_name="Purchase Date")),
                (
                    "warranty_period",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Unit: months",
                        null=True,
                        verbose_name="Warranty Period",
                    ),
                ),
                (
                    "warranty_expiration_date",
                    models.DateField(blank=True, editable=False, null=True, verbose_name="Warranty Expiration Date"),
                ),
                ("comments", models.TextField(blank=True, default="", verbose_name="Comments")),
                (
                    "asset_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="netbox_smartlock.assetgroup",
                        verbose_name="Asset Group",
                    ),
                ),
                (
                    "device",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="smartlock_asset",
                        to="dcim.device",
                        verbose_name="DCIM Device",
                    ),
                ),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "ordering": ("-last_updated", "name"),
                "verbose_name": "Asset",
                "verbose_name_plural": "Assets",
            },
        ),
        migrations.RunPython(backfill_assets_from_device_custom_fields, migrations.RunPython.noop),
        migrations.RunPython(remove_legacy_device_asset_custom_fields, migrations.RunPython.noop),
    ]
