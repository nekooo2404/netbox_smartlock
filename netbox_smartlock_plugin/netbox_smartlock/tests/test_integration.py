import csv
import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import ObjectType
from dcim.models import Location, Rack, Region, Site
from netbox.choices import CSVDelimiterChoices, ImportFormatChoices
from users.models import ObjectPermission

from upload_file_plugin.models import UploadedFile
from upload_file_plugin.services import sync_uploaded_files

from netbox_smartlock.api.serializers import SmartLockSerializer
from netbox_smartlock.contracts import SMARTLOCK_IMPORT_FIELD_NAMES
from netbox_smartlock.models import AssetGroup, SmartLock


class SmartLockIntegrationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="smartlock-user",
            password="test-password",
        )
        cls.region = Region.objects.create(name="Region 1", slug="region-1")
        cls.site = Site.objects.create(name="Site 1", slug="site-1", region=cls.region)
        cls.location = Location.objects.create(name="Room A", slug="room-a", site=cls.site)
        cls.rack = Rack.objects.create(name="R01", site=cls.site, location=cls.location)
        cls.asset_group = AssetGroup.objects.create(
            name="Door Locks",
            slug="door-locks",
            code="DL",
            status=AssetGroup.STATUS_ACTIVE,
        )

    @staticmethod
    def csv_text(rows):
        return "\n".join(rows)

    @classmethod
    def grant_object_permission(cls, model, actions):
        permission = ObjectPermission(name=f"{model.__name__} {','.join(actions)}", actions=actions)
        permission.save()
        permission.users.add(cls.user)
        permission.object_types.add(ObjectType.objects.get_for_model(model))
        return permission

    @staticmethod
    def grant_object_permission_to_user(user, model, actions, name_prefix="test", constraints=None):
        permission = ObjectPermission(
            name=f"{name_prefix} {user.username} {model._meta.label_lower} {','.join(actions)}",
            actions=actions,
            constraints=constraints,
        )
        permission.save()
        permission.users.add(user)
        permission.object_types.add(ObjectType.objects.get_for_model(model))
        return permission

    @classmethod
    def grant_smartlock_import_permissions(cls):
        cls.grant_object_permission(SmartLock, ["add", "change"])
        for model in (AssetGroup, Region, Site, Location, Rack):
            cls.grant_object_permission(model, ["view"])

    def login(self):
        self.client.force_login(self.user)

    def smartlock_row(self, *, code="SL-001", name="Front Door", rack_lookup="site-1|room-a|R01"):
        return (
            f",{name},{code},door-locks,active,,,"
            f"Smart Lock,M1,S1,GTSC,2026-01-01,2026-01-10,12,"
            f"region-1,site-1,room-a,{rack_lookup},front"
        )


class SmartLockCoreImportTest(SmartLockIntegrationTestBase):
    def post_import(self, rows):
        self.login()
        self.grant_smartlock_import_permissions()
        return self.client.post(
            reverse("plugins:netbox_smartlock:smartlock_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": self.csv_text(rows),
            },
        )

    def test_core_bulk_import_creates_smartlock_with_rack_mapping(self):
        response = self.post_import(
            [
                ",".join(SMARTLOCK_IMPORT_FIELD_NAMES),
                self.smartlock_row(),
            ]
        )

        self.assertEqual(response.status_code, 302)
        smartlock = SmartLock.objects.get(code="SL-001")
        self.assertEqual(smartlock.rack, self.rack)
        self.assertEqual(smartlock.site, self.site)
        self.assertEqual(smartlock.location, self.location)
        self.assertEqual(smartlock.region, self.region)
        self.assertEqual(smartlock.warranty_expiration_date.isoformat(), "2027-01-10")

    def test_core_bulk_import_is_atomic_when_later_row_is_invalid(self):
        response = self.post_import(
            [
                ",".join(SMARTLOCK_IMPORT_FIELD_NAMES),
                self.smartlock_row(code="SL-VALID"),
                self.smartlock_row(code="SL-BAD", rack_lookup="missing-rack"),
            ]
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SmartLock.objects.filter(code__in=["SL-VALID", "SL-BAD"]).exists())

    def test_core_csv_export_round_trips_to_core_import_contract(self):
        smartlock = SmartLock.objects.create(
            name="Back Door",
            code="SL-EXPORT",
            asset_group=self.asset_group,
            status=SmartLock.STATUS_ACTIVE,
            device_type="Smart Lock",
            model="M2",
            serial="S2",
            manufacturer="GTSC",
            bought_date="2026-01-10",
            warranty_period=12,
            region=self.region,
            site=self.site,
            location=self.location,
            rack=self.rack,
            rack_face=SmartLock.RACK_FACE_FRONT,
        )
        self.login()
        self.grant_object_permission(SmartLock, ["view"])

        response = self.client.get(reverse("plugins:netbox_smartlock:smartlock_list"), {"export": "table"})

        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(response.content.decode().splitlines()))
        row = next(item for item in rows if item["code"] == smartlock.code)
        self.assertEqual(tuple(row.keys()), SMARTLOCK_IMPORT_FIELD_NAMES)
        self.assertEqual(row["asset_group"], self.asset_group.slug)
        self.assertEqual(row["rack_lookup"], "site-1|room-a|R01")


class AssetGroupCoreImportTest(SmartLockIntegrationTestBase):
    def post_import(self, rows):
        self.login()
        self.grant_object_permission(AssetGroup, ["add", "change"])
        return self.client.post(
            reverse("plugins:netbox_smartlock:assetgroup_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": self.csv_text(rows),
            },
        )

    def test_assetgroup_core_import_url_exists(self):
        self.login()
        self.grant_object_permission(AssetGroup, ["add"])

        response = self.client.get(reverse("plugins:netbox_smartlock:assetgroup_bulk_import"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Nhóm tài sản")

    def test_assetgroup_list_does_not_render_missing_import_url(self):
        self.login()
        self.grant_object_permission(AssetGroup, ["view", "add"])

        response = self.client.get(reverse("plugins:netbox_smartlock:assetgroup_list"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("/plugins/smartlock/asset-groups/None", content)
        self.assertIn("/plugins/smartlock/asset-groups/import/", content)

    def test_assetgroup_core_import_creates_group(self):
        response = self.post_import(
            [
                "name,slug,code,status,description,comments",
                "Cabinet Locks,cabinet-locks,CL,active,Imported group,",
            ]
        )

        self.assertEqual(response.status_code, 302)
        asset_group = AssetGroup.objects.get(slug="cabinet-locks")
        self.assertEqual(asset_group.code, "CL")
        self.assertEqual(asset_group.description, "Imported group")


class SmartLockCrudViewTest(SmartLockIntegrationTestBase):
    def test_add_view_creates_smartlock_without_server_error(self):
        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        for model in (AssetGroup, Region, Site, Location, Rack):
            self.grant_object_permission(model, ["view"])

        response = self.client.post(
            reverse("plugins:netbox_smartlock:smartlock_add"),
            {
                "name": "Front Door UI",
                "code": "SL-UI-001",
                "asset_group": self.asset_group.pk,
                "status": SmartLock.STATUS_ACTIVE,
                "device_type": "Smart Lock",
                "model": "",
                "serial": "",
                "manufacturer": "",
                "setup_date": "",
                "bought_date": "",
                "warranty_period": "",
                "region": self.region.pk,
                "site": self.site.pk,
                "location": self.location.pk,
                "rack": self.rack.pk,
                "rack_face": "",
                "description": "",
                "comments": "",
                "upload_files": "[]",
            },
        )

        self.assertEqual(response.status_code, 302)
        smartlock = SmartLock.objects.get(code="SL-UI-001")
        self.assertEqual(smartlock.site, self.site)
        self.assertEqual(smartlock.location, self.location)
        self.assertEqual(smartlock.rack, self.rack)

    def test_add_form_rejects_out_of_scope_dcim_related_objects(self):
        other_region = Region.objects.create(name="Restricted Region UI", slug="restricted-region-ui")
        other_site = Site.objects.create(name="Restricted Site UI", slug="restricted-site-ui", region=other_region)
        other_location = Location.objects.create(name="Restricted Room UI", slug="restricted-room-ui", site=other_site)
        other_rack = Rack.objects.create(name="RR01", site=other_site, location=other_location)

        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        self.grant_object_permission(AssetGroup, ["view"])
        self.grant_object_permission_to_user(
            self.user,
            Region,
            ["view"],
            name_prefix="smartlock-form-scope",
            constraints={"slug": self.region.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Site,
            ["view"],
            name_prefix="smartlock-form-scope",
            constraints={"slug": self.site.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Location,
            ["view"],
            name_prefix="smartlock-form-scope",
            constraints={"slug": self.location.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Rack,
            ["view"],
            name_prefix="smartlock-form-scope",
            constraints={"name": self.rack.name},
        )

        response = self.client.post(
            reverse("plugins:netbox_smartlock:smartlock_add"),
            {
                "name": "Out Of Scope UI",
                "code": "SL-UI-SCOPE-BAD",
                "asset_group": self.asset_group.pk,
                "status": SmartLock.STATUS_ACTIVE,
                "device_type": "Smart Lock",
                "model": "",
                "serial": "",
                "manufacturer": "",
                "setup_date": "",
                "bought_date": "",
                "warranty_period": "",
                "region": other_region.pk,
                "site": other_site.pk,
                "location": other_location.pk,
                "rack": other_rack.pk,
                "rack_face": SmartLock.RACK_FACE_FRONT,
                "description": "",
                "comments": "",
                "upload_files": "[]",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SmartLock.objects.filter(code="SL-UI-SCOPE-BAD").exists())


class SmartLockPermissionTest(SmartLockIntegrationTestBase):
    def test_core_import_view_requires_add_permission(self):
        self.login()
        response = self.client.get(reverse("plugins:netbox_smartlock:smartlock_bulk_import"))

        self.assertEqual(response.status_code, 403)

    def test_core_import_view_allows_netbox_object_permission(self):
        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        response = self.client.get(reverse("plugins:netbox_smartlock:smartlock_bulk_import"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Import Khóa thông minh")

    def test_core_import_rejects_out_of_scope_dcim_rack_lookup(self):
        other_region = Region.objects.create(name="Restricted Region Import", slug="restricted-region-import")
        other_site = Site.objects.create(name="Restricted Site Import", slug="restricted-site-import", region=other_region)
        other_location = Location.objects.create(name="Restricted Room Import", slug="restricted-room-import", site=other_site)
        Rack.objects.create(name="IR01", site=other_site, location=other_location)

        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        self.grant_object_permission(AssetGroup, ["view"])
        self.grant_object_permission_to_user(
            self.user,
            Region,
            ["view"],
            name_prefix="smartlock-import-scope",
            constraints={"slug": self.region.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Site,
            ["view"],
            name_prefix="smartlock-import-scope",
            constraints={"slug": self.site.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Location,
            ["view"],
            name_prefix="smartlock-import-scope",
            constraints={"slug": self.location.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Rack,
            ["view"],
            name_prefix="smartlock-import-scope",
            constraints={"name": self.rack.name},
        )

        response = self.client.post(
            reverse("plugins:netbox_smartlock:smartlock_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": self.csv_text(
                    [
                        ",".join(SMARTLOCK_IMPORT_FIELD_NAMES),
                        self.smartlock_row(
                            code="SL-IMPORT-SCOPE-BAD",
                            name="Out Of Scope Import",
                            rack_lookup="restricted-site-import|restricted-room-import|IR01",
                        ).replace("region-1,site-1,room-a,", ",,,"),
                    ]
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SmartLock.objects.filter(code="SL-IMPORT-SCOPE-BAD").exists())


class SmartLockApiValidationTest(SmartLockIntegrationTestBase):
    def test_api_serializer_uses_shared_rack_mapping_validation(self):
        data = {
            "name": "  API Lock  ",
            "code": "  SL-API  ",
            "status": SmartLock.STATUS_ACTIVE,
            "asset_group_id": self.asset_group.pk,
            "device_type": "  Smart Lock  ",
            "region_id": self.region.pk,
            "site_id": self.site.pk,
            "location_id": self.location.pk,
            "rack_id": self.rack.pk,
            "rack_face": SmartLock.RACK_FACE_FRONT,
        }

        serializer = SmartLockSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "API Lock")
        self.assertEqual(serializer.validated_data["code"], "SL-API")
        self.assertEqual(serializer.validated_data["device_type"], "Smart Lock")
        self.assertEqual(serializer.validated_data["site"], self.site)
        self.assertEqual(serializer.validated_data["location"], self.location)
        self.assertEqual(serializer.validated_data["region"], self.region)

    def test_api_serializer_rejects_rack_site_mismatch(self):
        other_site = Site.objects.create(name="Site 2", slug="site-2", region=self.region)
        other_location = Location.objects.create(name="Room B", slug="room-b", site=other_site)
        data = {
            "name": "API Lock",
            "code": "SL-API-BAD",
            "status": SmartLock.STATUS_ACTIVE,
            "asset_group_id": self.asset_group.pk,
            "device_type": "Smart Lock",
            "region_id": self.region.pk,
            "site_id": other_site.pk,
            "location_id": other_location.pk,
            "rack_id": self.rack.pk,
        }

        serializer = SmartLockSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("rack", serializer.errors)

    def test_api_rejects_out_of_scope_dcim_related_objects(self):
        other_region = Region.objects.create(name="Restricted Region API", slug="restricted-region-api")
        other_site = Site.objects.create(name="Restricted Site API", slug="restricted-site-api", region=other_region)
        other_location = Location.objects.create(name="Restricted Room API", slug="restricted-room-api", site=other_site)
        other_rack = Rack.objects.create(name="AR01", site=other_site, location=other_location)

        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        self.grant_object_permission(AssetGroup, ["view"])
        self.grant_object_permission_to_user(
            self.user,
            Region,
            ["view"],
            name_prefix="smartlock-api-scope",
            constraints={"slug": self.region.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Site,
            ["view"],
            name_prefix="smartlock-api-scope",
            constraints={"slug": self.site.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Location,
            ["view"],
            name_prefix="smartlock-api-scope",
            constraints={"slug": self.location.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Rack,
            ["view"],
            name_prefix="smartlock-api-scope",
            constraints={"name": self.rack.name},
        )

        response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:smartlock-list"),
            data=json.dumps(
                {
                    "name": "Out Of Scope API",
                    "code": "SL-API-SCOPE-BAD",
                    "status": SmartLock.STATUS_ACTIVE,
                    "asset_group_id": self.asset_group.pk,
                    "device_type": "Smart Lock",
                    "region_id": other_region.pk,
                    "site_id": other_site.pk,
                    "location_id": other_location.pk,
                    "rack_id": other_rack.pk,
                    "rack_face": SmartLock.RACK_FACE_FRONT,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SmartLock.objects.filter(code="SL-API-SCOPE-BAD").exists())

    def test_api_rejects_inactive_asset_group(self):
        inactive_asset_group = AssetGroup.objects.create(
            name="Inactive Locks",
            slug="inactive-locks",
            code="IL",
            status=AssetGroup.STATUS_INACTIVE,
        )

        self.login()
        self.grant_object_permission(SmartLock, ["add"])
        self.grant_object_permission(AssetGroup, ["view"])
        for model in (Region, Site, Location, Rack):
            self.grant_object_permission(model, ["view"])

        response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:smartlock-list"),
            data=json.dumps(
                {
                    "name": "Inactive Asset Group API",
                    "code": "SL-API-INACTIVE-GROUP",
                    "status": SmartLock.STATUS_ACTIVE,
                    "asset_group_id": inactive_asset_group.pk,
                    "device_type": "Smart Lock",
                    "region_id": self.region.pk,
                    "site_id": self.site.pk,
                    "location_id": self.location.pk,
                    "rack_id": self.rack.pk,
                    "rack_face": SmartLock.RACK_FACE_FRONT,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SmartLock.objects.filter(code="SL-API-INACTIVE-GROUP").exists())


class SmartLockAttachmentLifecycleTest(SmartLockIntegrationTestBase):
    def make_smartlock(self):
        return SmartLock.objects.create(
            name="Attachment Lock",
            code="SL-FILE",
            asset_group=self.asset_group,
            status=SmartLock.STATUS_ACTIVE,
            device_type="Smart Lock",
            region=self.region,
            site=self.site,
            location=self.location,
            rack=self.rack,
        )

    def pending_payload(self, media_root, filename="lock.png", content=b"image-data"):
        tmp_dir = Path(media_root) / "uploads" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = tmp_dir / filename
        tmp_file.write_bytes(content)
        return [
            {
                "file_name": filename,
                "path": f"{settings.MEDIA_URL.rstrip('/')}/uploads/tmp/{filename}",
                "size": len(content),
            }
        ]

    def test_attachment_sync_add_remove_and_model_delete_cleanup(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                smartlock = self.make_smartlock()

                sync_uploaded_files(
                    smartlock,
                    json.dumps(self.pending_payload(media_root)),
                    model_name="smartlock",
                )

                uploaded = UploadedFile.objects.get(model_name="smartlock", object_id=smartlock.pk)
                stored_path = Path(media_root) / uploaded.file.name
                self.assertTrue(stored_path.exists())

                sync_uploaded_files(smartlock, "[]", model_name="smartlock")
                self.assertFalse(UploadedFile.objects.filter(pk=uploaded.pk).exists())
                self.assertFalse(stored_path.exists())

                sync_uploaded_files(
                    smartlock,
                    json.dumps(self.pending_payload(media_root, filename="lock-2.png")),
                    model_name="smartlock",
                )
                uploaded = UploadedFile.objects.get(model_name="smartlock", object_id=smartlock.pk)
                stored_path = Path(media_root) / uploaded.file.name

                smartlock.delete()

                self.assertFalse(UploadedFile.objects.filter(pk=uploaded.pk).exists())
                self.assertFalse(stored_path.exists())
