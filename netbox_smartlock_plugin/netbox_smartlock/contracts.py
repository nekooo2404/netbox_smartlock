from dataclasses import dataclass


@dataclass(frozen=True)
class ImportField:
    name: str
    required: bool = False
    help_text: str = ""


SMARTLOCK_IMPORT_FIELDS = (
    ImportField("id", help_text="Use id to update an existing Smart Lock during CSV round-trip import."),
    ImportField("name", required=True),
    ImportField("code", required=True),
    ImportField("asset_group", required=True, help_text="AssetGroup slug."),
    ImportField("status", required=True, help_text="One of: active, backup, maintenance, broken."),
    ImportField("description"),
    ImportField("comments"),
    ImportField("device_type", required=True),
    ImportField("model"),
    ImportField("serial"),
    ImportField("manufacturer"),
    ImportField("setup_date"),
    ImportField("bought_date"),
    ImportField("warranty_period"),
    ImportField("region", help_text="Region slug. Can be inferred from site/rack."),
    ImportField("site", help_text="Site slug. Can be inferred from location/rack."),
    ImportField("location", help_text="Location slug. Can be inferred from rack."),
    ImportField("rack_lookup", help_text="rack, site|rack, or site|location|rack."),
    ImportField("rack_face", help_text="front or rear."),
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
    "Required columns: name, code, asset_group, status, device_type. "
    "Use slugs for asset_group/region/site/location. "
    "Use id to update an existing record. "
    "rack_lookup supports rack, site|rack, or site|location|rack."
)

SMARTLOCK_IMPORT_HELP_ITEMS = (
    "`name`, `code`, `asset_group`, `status`, and `device_type` are required.",
    "`id` updates an existing Smart Lock when importing a round-trip CSV.",
    "`asset_group`, `region`, `site`, and `location` should use slugs.",
    "`rack_lookup` supports `rack`, `site|rack`, or `site|location|rack`.",
    "When `rack_lookup` is provided, SmartLock synchronizes site/location/region from the Rack.",
    "CSV import/export uses the core NetBox workflow. Excel is an additional SmartLock report.",
)
