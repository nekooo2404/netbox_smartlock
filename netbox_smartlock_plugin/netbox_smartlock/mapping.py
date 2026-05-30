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
    """Chuẩn hóa text đầu vào từ UI/API/import trước khi validate và lưu."""
    return str(value or "").strip()


def get_warranty_state(expiration_date, *, today=None):
    """Phân loại trạng thái bảo hành; mốc cảnh báo cố định là 30 ngày."""
    if not expiration_date:
        return WARRANTY_STATE_MISSING

    today = today or timezone.localdate()
    if expiration_date < today:
        return WARRANTY_STATE_EXPIRED
    if expiration_date <= today + timedelta(days=30):
        return WARRANTY_STATE_EXPIRING
    return WARRANTY_STATE_VALID


def format_rack_lookup(rack):
    """Sinh khóa import/export ổn định cho rack: site|location|rack khi có đủ dữ liệu."""
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
    """Tìm rack từ CSV, ưu tiên scope site/location đã chọn để tránh nhập nhầm rack trùng tên."""
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
            f"Tra cứu tủ rack phải dùng định dạng 'rack', 'site{RACK_LOOKUP_SEPARATOR}rack', "
            f"hoặc 'site{RACK_LOOKUP_SEPARATOR}location{RACK_LOOKUP_SEPARATOR}rack'."
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
        raise ValidationError(f"Không tìm thấy tủ rack '{value}'.")
    if len(matches) > 1:
        raise ValidationError(
            f"Tủ rack '{value}' bị trùng. Vui lòng bổ sung site/location trong giá trị import."
        )
    return matches[0]


def sync_smartlock_hierarchy(instance, errors=None):
    """Đồng bộ Region/Site/Location từ Rack/Location/Site DCIM và gom lỗi theo field."""
    errors = errors if errors is not None else {}

    if getattr(instance, "rack_id", None):
        rack = instance.rack

        if not getattr(rack, "site_id", None):
            errors["rack"] = "Tủ rack phải thuộc một địa điểm NetBox."
        elif getattr(instance, "site_id", None) and instance.site_id != rack.site_id:
            errors["rack"] = "Tủ rack phải thuộc địa điểm NetBox đã chọn."
        else:
            instance.site = rack.site

        rack_location_id = getattr(rack, "location_id", None)
        if rack_location_id:
            if getattr(instance, "location_id", None) and instance.location_id != rack_location_id:
                errors["rack"] = "Tủ rack phải thuộc vị trí NetBox đã chọn."
            else:
                instance.location = rack.location
        elif not getattr(instance, "location_id", None):
            errors["location"] = (
                "Tủ rack chưa có vị trí NetBox. Vui lòng cập nhật tủ rack hoặc chọn vị trí thủ công."
            )

    if getattr(instance, "location_id", None):
        location = instance.location
        if getattr(instance, "site_id", None) and instance.site_id != location.site_id:
            errors["location"] = "Vị trí phải thuộc địa điểm đã chọn."
        else:
            instance.site = location.site

    if getattr(instance, "site_id", None):
        site = instance.site
        site_region_id = getattr(site, "region_id", None)
        if not site_region_id:
            errors["site"] = "Địa điểm phải thuộc một khu vực NetBox trước khi ánh xạ khóa thông minh."
        elif getattr(instance, "region_id", None) and instance.region_id != site_region_id:
            errors["site"] = "Địa điểm phải thuộc khu vực đã chọn."
        else:
            instance.region = site.region

    if not getattr(instance, "site_id", None):
        errors.setdefault("site", "Bắt buộc chọn địa điểm.")
    if not getattr(instance, "location_id", None):
        errors.setdefault("location", "Bắt buộc chọn vị trí.")
    if not getattr(instance, "region_id", None):
        errors.setdefault("region", "Bắt buộc chọn khu vực.")

    return errors
