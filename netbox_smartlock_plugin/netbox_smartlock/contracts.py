from dataclasses import dataclass


@dataclass(frozen=True)
class ImportField:
    name: str
    required: bool = False
    help_text: str = ""


SMARTLOCK_IMPORT_FIELDS = (
    ImportField("id", help_text="Dùng id để cập nhật khóa thông minh đã có khi import lại CSV."),
    ImportField("name", required=True),
    ImportField("code", required=True),
    ImportField("asset_group", required=True, help_text="Slug nhóm tài sản."),
    ImportField("status", required=True, help_text="Một trong các giá trị: active, backup, maintenance, broken."),
    ImportField("description"),
    ImportField("comments"),
    ImportField("device_type", required=True),
    ImportField("model"),
    ImportField("serial"),
    ImportField("manufacturer"),
    ImportField("setup_date"),
    ImportField("bought_date"),
    ImportField("warranty_period"),
    ImportField("region", help_text="Slug khu vực. Có thể suy ra từ địa điểm/tủ rack."),
    ImportField("site", help_text="Slug địa điểm. Có thể suy ra từ vị trí/tủ rack."),
    ImportField("location", help_text="Slug vị trí. Có thể suy ra từ tủ rack."),
    ImportField("rack_lookup", help_text="rack, site|rack hoặc site|location|rack."),
    ImportField("rack_face", help_text="front hoặc rear."),
)

SMARTLOCK_IMPORT_FIELD_NAMES = tuple(field.name for field in SMARTLOCK_IMPORT_FIELDS)
SMARTLOCK_IMPORT_MODEL_FIELDS = tuple(
    field.name for field in SMARTLOCK_IMPORT_FIELDS if field.name != "rack_lookup"
)
SMARTLOCK_REQUIRED_IMPORT_FIELDS = tuple(
    field.name for field in SMARTLOCK_IMPORT_FIELDS if field.required
)

SMARTLOCK_EXCEL_EXTRA_FIELDS = ("rack_lookup", "warranty_state", "uploaded_files")
SMARTLOCK_CUSTOM_EXPORT_PARAM = "smartlock_export"
SMARTLOCK_EXPORT_EXCEL_REPORT = "excel_report"

SMARTLOCK_IMPORT_CSV_DESCRIPTION = (
    "Các cột bắt buộc: name, code, asset_group, status, device_type. "
    "Dùng slug cho asset_group/region/site/location. "
    "Dùng id để cập nhật bản ghi đã có. "
    "rack_lookup hỗ trợ rack, site|rack hoặc site|location|rack."
)

SMARTLOCK_IMPORT_HELP_ITEMS = (
    "Các cột `name`, `code`, `asset_group`, `status` và `device_type` là bắt buộc.",
    "`id` dùng để cập nhật khóa thông minh đã có khi import lại CSV.",
    "`asset_group`, `region`, `site` và `location` nên dùng slug.",
    "`rack_lookup` hỗ trợ `rack`, `site|rack` hoặc `site|location|rack`.",
    "Khi có `rack_lookup`, SmartLock đồng bộ địa điểm/vị trí/khu vực từ tủ rack.",
    "CSV import/export dùng workflow gốc của NetBox. Excel là báo cáo bổ sung của SmartLock.",
)
