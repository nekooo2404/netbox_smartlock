from django.core.exceptions import ValidationError

from .mapping import normalize_text, resolve_rack_lookup, sync_smartlock_hierarchy


SMARTLOCK_TEXT_FIELDS = (
    "name",
    "code",
    "device_type",
    "model",
    "serial",
    "manufacturer",
    "description",
    "comments",
)

SMARTLOCK_BASE_FIELDS = (
    "asset_group",
    "status",
    "setup_date",
    "bought_date",
    "warranty_period",
    "region",
    "site",
    "location",
    "rack",
    "rack_face",
)


def normalize_smartlock_text_fields(cleaned_data):
    cleaned_data = cleaned_data or {}
    for field_name in SMARTLOCK_TEXT_FIELDS:
        if field_name in cleaned_data:
            cleaned_data[field_name] = normalize_text(cleaned_data.get(field_name))
    return cleaned_data


def apply_smartlock_cleaned_data(instance, cleaned_data, *, include_rack=True):
    cleaned_data = cleaned_data or {}
    normalize_smartlock_text_fields(cleaned_data)

    for field_name in SMARTLOCK_TEXT_FIELDS:
        if field_name in cleaned_data:
            setattr(instance, field_name, cleaned_data.get(field_name))

    for field_name in SMARTLOCK_BASE_FIELDS:
        if field_name == "rack" and not include_rack:
            continue
        if field_name in cleaned_data:
            setattr(instance, field_name, cleaned_data.get(field_name))

    return instance


def validate_smartlock_hierarchy(instance):
    errors = {}
    sync_smartlock_hierarchy(instance, errors=errors)
    if errors:
        raise ValidationError(errors)
    return instance


def build_smartlock_candidate(instance=None, data=None):
    from .models import SmartLock

    candidate = SmartLock()
    if instance is not None:
        for field_name in (*SMARTLOCK_TEXT_FIELDS, *SMARTLOCK_BASE_FIELDS):
            setattr(candidate, field_name, getattr(instance, field_name, None))

    if data:
        apply_smartlock_cleaned_data(candidate, data)

    return candidate


def normalize_smartlock_form_data(instance, cleaned_data):
    apply_smartlock_cleaned_data(instance, cleaned_data)
    validate_smartlock_hierarchy(instance)
    return cleaned_data


def normalize_smartlock_import_data(instance, cleaned_data):
    rack_lookup = normalize_text(cleaned_data.get("rack_lookup"))
    if rack_lookup:
        try:
            cleaned_data["rack"] = resolve_rack_lookup(
                rack_lookup,
                site=cleaned_data.get("site"),
                location=cleaned_data.get("location"),
            )
        except ValidationError as exc:
            raise ValidationError({"rack_lookup": exc.messages})
    else:
        cleaned_data["rack"] = None

    apply_smartlock_cleaned_data(instance, cleaned_data)
    validate_smartlock_hierarchy(instance)
    return cleaned_data


def normalize_smartlock_api_data(instance, attrs):
    candidate = build_smartlock_candidate(instance, attrs)
    validate_smartlock_hierarchy(candidate)

    for field_name in SMARTLOCK_TEXT_FIELDS:
        if field_name in attrs:
            attrs[field_name] = getattr(candidate, field_name)

    for field_name in ("region", "site", "location", "rack"):
        attrs[field_name] = getattr(candidate, field_name, None)

    return attrs
