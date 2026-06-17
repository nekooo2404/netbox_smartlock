from django.test import SimpleTestCase
from netbox_smartlock.contracts import (
    SMARTLOCK_CUSTOM_EXPORT_PARAM,
    SMARTLOCK_EXPORT_EXCEL_REPORT,
    SMARTLOCK_IMPORT_FIELD_NAMES,
    SMARTLOCK_IMPORT_MODEL_FIELDS,
    SMARTLOCK_REQUIRED_IMPORT_FIELDS,
)
from netbox_smartlock.exports import SmartLockExportService
from netbox_smartlock.exports import excel_cell_value
from netbox_smartlock.exports import AccessRequestExportService, AssetGroupExportService, DeviceAssetExportService
from netbox.tables import columns
from netbox_smartlock.tables import DeviceAssetTable


class SmartLockImportExportContractTest(SimpleTestCase):
    def test_csv_contract_has_expected_round_trip_fields(self):
        self.assertEqual(
            SMARTLOCK_IMPORT_FIELD_NAMES,
            (
                "id",
                "name",
                "code",
                "asset_group",
                "status",
                "description",
                "comments",
                "device_type",
                "model",
                "serial",
                "manufacturer",
                "setup_date",
                "bought_date",
                "warranty_period",
                "region",
                "site",
                "location",
                "rack_lookup",
                "rack_face",
            ),
        )

    def test_import_model_fields_exclude_virtual_rack_lookup(self):
        self.assertNotIn("rack_lookup", SMARTLOCK_IMPORT_MODEL_FIELDS)
        self.assertIn("rack_face", SMARTLOCK_IMPORT_MODEL_FIELDS)

    def test_required_fields_are_documented_in_contract(self):
        self.assertEqual(
            SMARTLOCK_REQUIRED_IMPORT_FIELDS,
            ("name", "code", "asset_group", "status", "device_type"),
        )

    def test_custom_export_param_does_not_override_netbox_core_export_param(self):
        self.assertEqual(SMARTLOCK_CUSTOM_EXPORT_PARAM, "smartlock_export")
        self.assertNotEqual(SMARTLOCK_CUSTOM_EXPORT_PARAM, "export")
        self.assertEqual(SMARTLOCK_EXPORT_EXCEL_REPORT, "excel_report")

    def test_core_csv_serializer_uses_import_contract_keys(self):
        asset_group = type("AssetGroupRef", (), {"slug": "locks"})()
        region = type("RegionRef", (), {"slug": "north"})()
        site = type("SiteRef", (), {"slug": "dc1"})()
        location = type("LocationRef", (), {"slug": "room-a"})()
        rack = type(
            "RackRef",
            (),
            {
                "name": "R01",
                "site_id": 1,
                "site": site,
                "location_id": 1,
                "location": location,
            },
        )()
        obj = type(
            "SmartLockRef",
            (),
            {
                "pk": 42,
                "name": "Front Door",
                "code": "SL-001",
                "asset_group": asset_group,
                "status": "active",
                "description": "",
                "comments": "",
                "device_type": "Smart Lock",
                "model": "M1",
                "serial": "S1",
                "manufacturer": "GTSC",
                "setup_date": None,
                "bought_date": None,
                "warranty_period": "",
                "region": region,
                "site": site,
                "location": location,
                "rack": rack,
                "rack_face": "front",
            },
        )()

        row = SmartLockExportService.serialize_core_csv_row(obj)

        self.assertEqual(tuple(row.keys()), SMARTLOCK_IMPORT_FIELD_NAMES)
        self.assertEqual(row["rack_lookup"], "dc1|room-a|R01")

    def test_excel_cell_value_strips_html_badges(self):
        value = '<span class="badge text-bg-success">Còn bảo hành</span>'

        self.assertEqual(excel_cell_value(value), "Còn bảo hành")

    def test_excel_export_services_keep_distinct_custom_params(self):
        self.assertEqual(AssetGroupExportService.custom_export_param, "assetgroup_export")
        self.assertEqual(DeviceAssetExportService.custom_export_param, "device_asset_export")
        self.assertEqual(SmartLockExportService.custom_export_param, "smartlock_export")
        self.assertEqual(AccessRequestExportService.custom_export_param, "accessrequest_export")

        for service in (
            AssetGroupExportService,
            DeviceAssetExportService,
            SmartLockExportService,
            AccessRequestExportService,
        ):
            self.assertEqual(service.custom_export_value, "excel_report")


class DeviceAssetActionsColumnContractTest(SimpleTestCase):
    def test_device_asset_actions_use_netbox_standard_actions_column(self):
        self.assertIs(type(DeviceAssetTable.base_columns["actions"]), columns.ActionsColumn)
