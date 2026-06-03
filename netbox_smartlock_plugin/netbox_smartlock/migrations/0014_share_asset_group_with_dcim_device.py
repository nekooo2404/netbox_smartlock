from django.db import migrations


FIELD_NAME = "smartlock_asset_group"
FIELD_LABEL = "Nhóm tài sản"
FIELD_DESCRIPTION = "Nhóm tài sản dùng chung cho Tài sản DCIM và SmartLock."
FIELD_RELATED_OBJECT_FILTER = {"status": "active"}
DEVICE_ASSET_STATUS_CUSTOM_FIELD = "smartlock_asset_status"
DEVICE_ASSET_STATUS_CHOICE_SET = "SmartLock DCIM Asset Status"
DEVICE_ASSET_STATUS_CHOICES = (
    ("active", "Đang hoạt động"),
    ("backup", "Dự phòng"),
    ("maintenance", "Bảo trì"),
    ("broken", "Hỏng"),
)
DEVICE_ASSET_CUSTOM_FIELD_DEFINITIONS = (
    {
        "name": FIELD_NAME,
        "type": "object",
        "label": FIELD_LABEL,
        "description": FIELD_DESCRIPTION,
        "required": True,
        "related_object_filter": FIELD_RELATED_OBJECT_FILTER,
    },
    {
        "name": DEVICE_ASSET_STATUS_CUSTOM_FIELD,
        "type": "select",
        "label": "Trạng thái tài sản",
        "description": "Trạng thái nghiệp vụ của tài sản theo DCIM.",
        "required": True,
        "default": "active",
        "choice_set_name": DEVICE_ASSET_STATUS_CHOICE_SET,
    },
    {
        "name": "smartlock_asset_description",
        "type": "longtext",
        "label": "Mô tả tài sản",
        "description": "Mô tả nghiệp vụ của tài sản theo DCIM, tối đa 500 ký tự.",
        "required": False,
        "validation_regex": r"(?s)^.{0,500}$",
    },
    {
        "name": "smartlock_setup_date",
        "type": "date",
        "label": "Ngày lắp đặt",
        "description": "Ngày lắp đặt tài sản theo DCIM.",
        "required": False,
    },
    {
        "name": "smartlock_bought_date",
        "type": "date",
        "label": "Ngày mua",
        "description": "Ngày mua tài sản theo DCIM.",
        "required": False,
    },
    {
        "name": "smartlock_warranty_period",
        "type": "integer",
        "label": "Thời hạn bảo hành",
        "description": "Thời hạn bảo hành của tài sản, đơn vị tháng.",
        "required": False,
        "validation_minimum": 1,
    },
    {
        "name": "smartlock_warranty_expiration_date",
        "type": "date",
        "label": "Thời gian bảo hành",
        "description": "Ngày hết hạn bảo hành, tự tính bằng Ngày mua + Thời hạn bảo hành.",
        "required": False,
        "ui_editable": "no",
    },
)
DEVICE_ASSET_CUSTOM_FIELD_NAMES = tuple(definition["name"] for definition in DEVICE_ASSET_CUSTOM_FIELD_DEFINITIONS)


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


def custom_field_model_fields(CustomField):
    return {field.name for field in CustomField._meta.get_fields()}


def set_if_available(instance, field_names, field_name, value, changed_fields):
    if field_name not in field_names:
        return

    if getattr(instance, field_name, None) == value:
        return

    setattr(instance, field_name, value)
    changed_fields.append(field_name)


def build_custom_field_defaults(definition, custom_field_fields, asset_group_object_type, choice_set=None):
    defaults = {
        "type": definition["type"],
        "label": definition["label"],
        "description": definition["description"],
        "required": definition.get("required", False),
    }
    if definition["name"] == FIELD_NAME and "related_object_type" in custom_field_fields:
        defaults["related_object_type"] = asset_group_object_type
    if "related_object_filter" in definition and "related_object_filter" in custom_field_fields:
        defaults["related_object_filter"] = definition["related_object_filter"]
    if "validation_minimum" in definition and "validation_minimum" in custom_field_fields:
        defaults["validation_minimum"] = definition["validation_minimum"]
    if "validation_regex" in definition and "validation_regex" in custom_field_fields:
        defaults["validation_regex"] = definition["validation_regex"]
    if "default" in definition and "default" in custom_field_fields:
        defaults["default"] = definition["default"]
    if "ui_editable" in definition and "ui_editable" in custom_field_fields:
        defaults["ui_editable"] = definition["ui_editable"]
    if choice_set is not None and "choice_set" in custom_field_fields:
        defaults["choice_set"] = choice_set
    return defaults


def ensure_device_asset_status_choice_set(apps):
    CustomFieldChoiceSet = apps.get_model("extras", "CustomFieldChoiceSet")
    choice_set, _ = CustomFieldChoiceSet.objects.get_or_create(
        name=DEVICE_ASSET_STATUS_CHOICE_SET,
        defaults={
            "extra_choices": [list(choice) for choice in DEVICE_ASSET_STATUS_CHOICES],
            "choice_colors": {
                "active": "green",
                "backup": "blue",
                "maintenance": "yellow",
                "broken": "red",
            },
        },
    )

    desired_choices = [list(choice) for choice in DEVICE_ASSET_STATUS_CHOICES]
    desired_colors = {
        "active": "green",
        "backup": "blue",
        "maintenance": "yellow",
        "broken": "red",
    }
    changed_fields = []
    if choice_set.extra_choices != desired_choices:
        choice_set.extra_choices = desired_choices
        changed_fields.append("extra_choices")
    if choice_set.choice_colors != desired_colors:
        choice_set.choice_colors = desired_colors
        changed_fields.append("choice_colors")
    if changed_fields:
        choice_set.save(update_fields=changed_fields)

    return choice_set


def ensure_device_asset_custom_fields(apps, schema_editor):
    CustomField = apps.get_model("extras", "CustomField")
    ObjectType = apps.get_model("core", "ObjectType")
    Device = apps.get_model("dcim", "Device")
    AssetGroup = apps.get_model("netbox_smartlock", "AssetGroup")

    device_object_type = get_object_type(ObjectType, Device)
    asset_group_object_type = get_object_type(ObjectType, AssetGroup)
    if device_object_type is None or asset_group_object_type is None:
        return

    custom_field_fields = custom_field_model_fields(CustomField)
    status_choice_set = ensure_device_asset_status_choice_set(apps)

    for definition in DEVICE_ASSET_CUSTOM_FIELD_DEFINITIONS:
        choice_set = status_choice_set if definition.get("choice_set_name") == DEVICE_ASSET_STATUS_CHOICE_SET else None
        defaults = build_custom_field_defaults(
            definition,
            custom_field_fields,
            asset_group_object_type,
            choice_set=choice_set,
        )
        custom_field, _ = CustomField.objects.get_or_create(name=definition["name"], defaults=defaults)

        changed_fields = []
        for field_name, value in defaults.items():
            set_if_available(custom_field, custom_field_fields, field_name, value, changed_fields)

        if changed_fields:
            custom_field.save(update_fields=changed_fields)

        if hasattr(custom_field, "object_types"):
            custom_field.object_types.add(device_object_type)
        elif hasattr(custom_field, "content_types"):
            custom_field.content_types.add(device_object_type)


def remove_device_asset_custom_fields(apps, schema_editor):
    CustomField = apps.get_model("extras", "CustomField")
    ObjectType = apps.get_model("core", "ObjectType")
    Device = apps.get_model("dcim", "Device")

    device_object_type = get_object_type(ObjectType, Device)
    if device_object_type is None:
        return

    for custom_field in CustomField.objects.filter(name__in=DEVICE_ASSET_CUSTOM_FIELD_NAMES):
        if hasattr(custom_field, "object_types"):
            custom_field.object_types.remove(device_object_type)
            if not custom_field.object_types.exists():
                custom_field.delete()
        elif hasattr(custom_field, "content_types"):
            custom_field.content_types.remove(device_object_type)
            if not custom_field.content_types.exists():
                custom_field.delete()

    CustomFieldChoiceSet = apps.get_model("extras", "CustomFieldChoiceSet")
    CustomFieldChoiceSet.objects.filter(name=DEVICE_ASSET_STATUS_CHOICE_SET).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_smartlock", "0013_rename_access_history_in_out_actions"),
    ]

    operations = [
        migrations.RunPython(
            ensure_device_asset_custom_fields,
            remove_device_asset_custom_fields,
        ),
    ]
