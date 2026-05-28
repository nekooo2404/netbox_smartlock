from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from dcim.models import Rack

RACK_LOOKUP_SEPARATOR = "|"

WARRANTY_STATE_VALID = "valid"
WARRANTY_STATE_EXPIRING = "expiring"
WARRANTY_STATE_EXPIRED = "expired"
WARRANTY_STATE_MISSING = "missing"

WARRANTY_STATE_CHOICES = (
    (WARRANTY_STATE_VALID, "Valid"),
    (WARRANTY_STATE_EXPIRING, "Expiring soon"),
    (WARRANTY_STATE_EXPIRED, "Expired"),
    (WARRANTY_STATE_MISSING, "Not set"),
)


def normalize_text(value):
    return str(value or "").strip()


def get_warranty_state(expiration_date, *, today=None):
    if not expiration_date:
        return WARRANTY_STATE_MISSING

    today = today or timezone.localdate()
    if expiration_date < today:
        return WARRANTY_STATE_EXPIRED
    if expiration_date <= today + timedelta(days=30):
        return WARRANTY_STATE_EXPIRING
    return WARRANTY_STATE_VALID


def format_rack_lookup(rack):
    if not rack:
        return ""

    parts = []
    if getattr(rack, "site_id", None) and getattr(rack.site, "slug", None):
        parts.append(rack.site.slug)
    if getattr(rack, "location_id", None) and getattr(rack.location, "slug", None):
        parts.append(rack.location.slug)
    parts.append(rack.name)
    return RACK_LOOKUP_SEPARATOR.join(parts)


def resolve_rack_lookup(raw_value, *, site=None, location=None):
    value = normalize_text(raw_value)
    if not value:
        return None

    parts = [part.strip() for part in value.split(RACK_LOOKUP_SEPARATOR) if part.strip()]
    site_slug = None
    location_slug = None

    if len(parts) == 1:
        rack_name = parts[0]
    elif len(parts) == 2:
        site_slug, rack_name = parts
    elif len(parts) == 3:
        site_slug, location_slug, rack_name = parts
    else:
        raise ValidationError(
            f"Rack lookup must use 'rack', 'site{RACK_LOOKUP_SEPARATOR}rack', "
            f"or 'site{RACK_LOOKUP_SEPARATOR}location{RACK_LOOKUP_SEPARATOR}rack'."
        )

    queryset = Rack.objects.select_related("site", "location")
    if location is not None:
        queryset = queryset.filter(location=location)
    elif location_slug:
        queryset = queryset.filter(location__slug=location_slug)

    if site is not None:
        queryset = queryset.filter(site=site)
    elif site_slug:
        queryset = queryset.filter(site__slug=site_slug)

    matches = list(queryset.filter(name=rack_name)[:2])
    if not matches:
        raise ValidationError(f"Rack '{value}' was not found.")
    if len(matches) > 1:
        raise ValidationError(
            f"Rack '{value}' is ambiguous. Include site/location in the import value."
        )
    return matches[0]


def sync_smartlock_hierarchy(instance, errors=None):
    errors = errors if errors is not None else {}

    if getattr(instance, "rack_id", None):
        rack = instance.rack

        if not getattr(rack, "site_id", None):
            errors["rack"] = "Rack must belong to a NetBox Site."
        elif getattr(instance, "site_id", None) and instance.site_id != rack.site_id:
            errors["rack"] = "Rack must belong to the selected NetBox Site."
        else:
            instance.site = rack.site

        rack_location_id = getattr(rack, "location_id", None)
        if rack_location_id:
            if getattr(instance, "location_id", None) and instance.location_id != rack_location_id:
                errors["rack"] = "Rack must belong to the selected NetBox Location."
            else:
                instance.location = rack.location
        elif not getattr(instance, "location_id", None):
            errors["location"] = (
                "Rack has no NetBox Location. Update the Rack or select a Location manually."
            )

    if getattr(instance, "location_id", None):
        location = instance.location
        if getattr(instance, "site_id", None) and instance.site_id != location.site_id:
            errors["location"] = "Location must belong to the selected Site."
        else:
            instance.site = location.site

    if getattr(instance, "site_id", None):
        site = instance.site
        site_region_id = getattr(site, "region_id", None)
        if not site_region_id:
            errors["site"] = "Site must belong to a NetBox Region before Smart Lock mapping."
        elif getattr(instance, "region_id", None) and instance.region_id != site_region_id:
            errors["site"] = "Site must belong to the selected Region."
        else:
            instance.region = site.region

    if not getattr(instance, "site_id", None):
        errors.setdefault("site", "Site is required.")
    if not getattr(instance, "location_id", None):
        errors.setdefault("location", "Location is required.")
    if not getattr(instance, "region_id", None):
        errors.setdefault("region", "Region is required.")

    return errors
