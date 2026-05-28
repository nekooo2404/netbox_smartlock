from datetime import date

import csv
import json
import tempfile
from io import BytesIO, StringIO
from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.choices import ObjectChangeActionChoices
from core.models import ObjectType
from core.models.change_logging import ObjectChange
from dcim.models import Location, Region, Site
from netbox.choices import CSVDelimiterChoices, ImportFormatChoices
from users.models import Group
from users.models import ObjectPermission
from upload_file_plugin.models import UploadedFile
from upload_file_plugin.views import delete_temp_file_view


class AccessRequestDomainTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="guest-user",
            password="test-password",
        )
        cls.region = Region.objects.create(name="North", slug="north")
        cls.site = Site.objects.create(name="DC 1", slug="dc-1", region=cls.region)
        cls.location = Location.objects.create(name="Room A", slug="room-a", site=cls.site)
        cls.other_region = Region.objects.create(name="South", slug="south")
        cls.other_site = Site.objects.create(name="DC 2", slug="dc-2", region=cls.other_region)
        cls.other_location = Location.objects.create(name="Room B", slug="room-b", site=cls.other_site)

    @staticmethod
    def model(name):
        try:
            return apps.get_model("netbox_smartlock", name)
        except LookupError as exc:
            raise AssertionError(f"{name} model is not registered") from exc

    def make_request(self, **overrides):
        AccessRequest = self.model("AccessRequest")
        data = {
            "name": "  Maintenance Visit  ",
            "expected_date": date(2026, 6, 1),
            "reason": "  Replace access controller  ",
            "region": self.region,
            "site": self.site,
        }
        data.update(overrides)
        return AccessRequest.objects.create(**data)

    def make_person(self, request, **overrides):
        AccessRequestPerson = self.model("AccessRequestPerson")
        data = {
            "request": request,
            "identity_code": "123456789012",
            "full_name": "  Nguyen Van A  ",
            "organization": "  Partner Co  ",
            "title": "  Engineer  ",
            "phone": "0912345678",
            "location": self.location,
            "description": "  Camera maintenance  ",
        }
        data.update(overrides)
        return AccessRequestPerson.objects.create(**data)

    def test_guest_request_defaults_and_submit_rules(self):
        AccessRequest = self.model("AccessRequest")
        AccessRequestHistory = self.model("AccessRequestHistory")

        request = self.make_request()

        self.assertEqual(str(request), "Maintenance Visit")
        self.assertEqual(request.status, AccessRequest.STATUS_DRAFT)
        self.assertEqual(request.reason, "Replace access controller")
        self.assertTrue(request.can_guest_edit)
        self.assertTrue(request.can_guest_delete)
        self.assertFalse(request.can_submit)

        with self.assertRaises(ValidationError):
            request.submit(user=self.user)

        self.make_person(request)
        request.submit(user=self.user)
        request.refresh_from_db()

        self.assertEqual(request.status, AccessRequest.STATUS_SUBMITTED)
        self.assertFalse(request.can_submit)
        self.assertTrue(
            AccessRequestHistory.objects.filter(
                request=request,
                actor=self.user,
                action=AccessRequestHistory.ACTION_SUBMIT,
                status=AccessRequest.STATUS_SUBMITTED,
            ).exists()
        )

    def test_admin_workflow_rules(self):
        AccessRequest = self.model("AccessRequest")
        AccessRequestPerson = self.model("AccessRequestPerson")
        AccessRequestHistory = self.model("AccessRequestHistory")

        request = self.make_request(name="Admin Flow")
        person = self.make_person(request)
        request.submit(user=self.user)
        request.refresh_from_db()

        self.assertTrue(request.can_admin_confirm)
        request.confirm(user=self.user, description="Received by admin")
        request.refresh_from_db()

        self.assertEqual(request.status, AccessRequest.STATUS_CONFIRMED)
        self.assertTrue(person.can_admin_verify)

        person.mark_invalid(user=self.user)
        person.refresh_from_db()
        self.assertEqual(person.verify_status, AccessRequestPerson.VERIFY_INVALID)

        with self.assertRaises(ValidationError):
            request.reject(user=self.user)

        with self.assertRaises(ValidationError):
            request.accept(user=self.user)

        person.mark_valid(user=self.user)
        person.refresh_from_db()
        self.assertEqual(person.verify_status, AccessRequestPerson.VERIFY_VALID)

        request.accept(user=self.user, description="Approved")
        request.refresh_from_db()
        person.refresh_from_db()

        self.assertEqual(request.status, AccessRequest.STATUS_ACCEPTED)
        self.assertTrue(person.can_check_in)
        person.check_in(user=self.user)
        person.refresh_from_db()
        self.assertEqual(person.access_status, AccessRequestPerson.ACCESS_IN)
        self.assertTrue(person.can_check_out)
        person.check_out(user=self.user)
        person.refresh_from_db()
        self.assertEqual(person.access_status, AccessRequestPerson.ACCESS_OUT)

        request.complete(user=self.user)
        request.refresh_from_db()
        self.assertEqual(request.status, AccessRequest.STATUS_COMPLETED)
        self.assertTrue(
            AccessRequestHistory.objects.filter(
                request=request,
                action=AccessRequestHistory.ACTION_COMPLETE,
            ).exists()
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_submit_notifies_active_admin_group_users(self):
        admin_group = Group.objects.create(name="Admin")
        admin_user = get_user_model().objects.create_user(
            username="security-admin",
            email="security-admin@example.com",
            password="test-password",
        )
        admin_user.groups.add(admin_group)
        inactive_admin = get_user_model().objects.create_user(
            username="inactive-admin",
            email="inactive-admin@example.com",
            password="test-password",
            is_active=False,
        )
        inactive_admin.groups.add(admin_group)
        request = self.make_request(name="Notify Admin")
        self.make_person(request)

        request.submit(user=self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["security-admin@example.com"])
        self.assertIn("Notify Admin", mail.outbox[0].subject)

    def test_request_site_must_belong_to_selected_region(self):
        with self.assertRaises(ValidationError) as ctx:
            self.make_request(site=self.other_site)

        self.assertIn("site", ctx.exception.message_dict)

    def test_person_validation_and_guest_action_rules(self):
        AccessRequestPerson = self.model("AccessRequestPerson")
        request = self.make_request()
        person = self.make_person(request)

        self.assertEqual(str(person), "Nguyen Van A")
        self.assertEqual(person.verify_status, AccessRequestPerson.VERIFY_PENDING)
        self.assertEqual(person.full_name, "Nguyen Van A")
        self.assertEqual(person.organization, "Partner Co")
        self.assertTrue(person.can_guest_edit)
        self.assertTrue(person.can_guest_delete)

        with self.assertRaises(ValidationError) as location_ctx:
            self.make_person(
                request,
                identity_code="123456789013",
                location=self.other_location,
            )
        self.assertIn("location", location_ctx.exception.message_dict)

        with self.assertRaises(ValidationError) as identity_ctx:
            self.make_person(request, identity_code="12345")
        self.assertIn("identity_code", identity_ctx.exception.message_dict)

        with self.assertRaises(ValidationError) as phone_ctx:
            self.make_person(request, identity_code="123456789014", phone="123")
        self.assertIn("phone", phone_ctx.exception.message_dict)
        with self.assertRaises(ValidationError) as phone_prefix_ctx:
            self.make_person(request, identity_code="123456789015", phone="0112345678")
        self.assertIn("phone", phone_prefix_ctx.exception.message_dict)

        with self.assertRaises(ValidationError):
            self.make_person(request)

        person.verify_status = AccessRequestPerson.VERIFY_VALID
        person.save()
        self.assertFalse(person.can_guest_edit)
        self.assertFalse(person.can_guest_delete)

    def test_rejected_request_allows_guest_to_rework_verified_person(self):
        request = self.make_request(name="Rejected Rework")
        person = self.make_person(request)
        request.submit(user=self.user)
        request.confirm(user=self.user)
        person.mark_valid(user=self.user)
        request.reject(user=self.user, description="Need updated guest information")
        request.refresh_from_db()
        person.refresh_from_db()

        self.assertTrue(request.can_guest_edit)
        self.assertTrue(request.can_guest_delete)
        self.assertTrue(person.can_guest_edit)
        self.assertTrue(person.can_guest_delete)

    def test_reject_requires_confirmed_status(self):
        AccessRequest = self.model("AccessRequest")

        request = self.make_request(name="Reject Must Confirm")
        self.make_person(request)
        request.submit(user=self.user)

        with self.assertRaises(ValidationError):
            request.reject(user=self.user, description="Rejected before confirmation")

        request.refresh_from_db()
        self.assertEqual(request.status, AccessRequest.STATUS_SUBMITTED)

        request.confirm(user=self.user)
        request.reject(user=self.user, description="Confirmed rejection reason")
        request.refresh_from_db()

        self.assertEqual(request.status, AccessRequest.STATUS_REJECTED)


class AccessRequestIntegrationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="guest-ui",
            password="test-password",
        )
        cls.region = Region.objects.create(name="North UI", slug="north-ui")
        cls.site = Site.objects.create(name="DC UI", slug="dc-ui", region=cls.region)
        cls.location = Location.objects.create(name="Room UI", slug="room-ui", site=cls.site)
        cls.other_region = Region.objects.create(name="South UI", slug="south-ui")
        cls.other_site = Site.objects.create(name="DC UI 2", slug="dc-ui-2", region=cls.other_region)
        cls.other_location = Location.objects.create(name="Room UI 2", slug="room-ui-2", site=cls.other_site)

    @property
    def AccessRequest(self):
        return apps.get_model("netbox_smartlock", "AccessRequest")

    @property
    def AccessRequestPerson(self):
        return apps.get_model("netbox_smartlock", "AccessRequestPerson")

    @property
    def AccessRequestHistory(self):
        return apps.get_model("netbox_smartlock", "AccessRequestHistory")

    @classmethod
    def grant_object_permission(cls, model, actions):
        permission = ObjectPermission(name=f"{model.__name__} access {','.join(actions)}", actions=actions)
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

    def login(self):
        self.client.force_login(self.user)

    def make_request(self, **overrides):
        data = {
            "name": "Guest Maintenance",
            "expected_date": date(2026, 6, 2),
            "reason": "Fix rack camera",
            "region": self.region,
            "site": self.site,
            "created_by": self.user,
        }
        data.update(overrides)
        return self.AccessRequest.objects.create(**data)

    def make_person(self, request, **overrides):
        data = {
            "request": request,
            "identity_code": "111122223333",
            "full_name": "Tran Thi B",
            "organization": "Partner Co",
            "title": "Technician",
            "phone": "0987654321",
            "location": self.location,
            "description": "Camera inspection",
        }
        data.update(overrides)
        return self.AccessRequestPerson.objects.create(**data)

    def make_created_request(self, user, **overrides):
        access_request = self.make_request(**overrides)
        access_request.created_by = user
        access_request.save(update_fields=("created_by", "last_updated"))
        return access_request

    @staticmethod
    def pending_payload(media_root, filename="access.png", content=b"image-data"):
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

    @staticmethod
    def csv_text(headers, row):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)
        return output.getvalue()

    @staticmethod
    def serializer_class(name):
        serializers = import_module("netbox_smartlock.api.serializers")
        try:
            return getattr(serializers, name)
        except AttributeError as exc:
            raise AssertionError(f"{name} serializer is not registered") from exc

    def test_access_request_crud_urls_use_netbox_generic_views(self):
        self.login()
        for model in (self.AccessRequest, self.AccessRequestPerson):
            self.grant_object_permission(model, ["view", "add", "change", "delete"])
        for model in (Region, Site, Location):
            self.grant_object_permission(model, ["view"])

        list_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Access Requests")
        self.assertContains(list_response, "Configure Table")
        self.assertContains(list_response, "Export Excel")
        list_content = list_response.content.decode()
        self.assertNotIn('href="None"', list_content)
        self.assertNotIn('formaction="None"', list_content)
        self.assertNotIn("/plugins/smartlock/access-requests/None", list_content)
        self.assertIn("/plugins/smartlock/access-requests/import/", list_content)
        self.assertIn("/plugins/smartlock/access-requests/edit/", list_content)
        self.assertIn("/plugins/smartlock/access-requests/delete/", list_content)

        add_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_add"),
            {
                "name": "Guest UI Flow",
                "expected_date": "2026-06-02",
                "reason": "Fix rack camera",
                "region": self.region.pk,
                "site": self.site.pk,
            },
        )
        form = add_response.context.get("form") if add_response.context else None
        self.assertEqual(add_response.status_code, 302, form.errors.as_json() if form else add_response.content.decode())
        access_request = self.AccessRequest.objects.get(name="Guest UI Flow")

        detail_response = self.client.get(access_request.get_absolute_url())
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Guest UI Flow")
        self.assertContains(detail_response, "Request History")
        self.assertContains(detail_response, "Persons")
        self.assertNotContains(detail_response, "Send Request")

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                person_add_response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_add"),
                    {
                        "request": access_request.pk,
                        "identity_code": "111122223333",
                        "full_name": "Tran Thi B",
                        "organization": "Partner Co",
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": self.location.pk,
                        "description": "Camera inspection",
                        "upload_files": json.dumps(self.pending_payload(media_root)),
                    },
                )
                self.assertEqual(person_add_response.status_code, 302)
                person = self.AccessRequestPerson.objects.get(identity_code="111122223333")
                self.assertTrue(
                    UploadedFile.objects.filter(
                        model_name="accessrequestperson",
                        object_id=person.pk,
                    ).exists()
                )

        detail_response = self.client.get(access_request.get_absolute_url())
        self.assertContains(detail_response, "Send Request")
        self.assertContains(detail_response, "Tran Thi B")
        self.assertContains(detail_response, "access.png")
        self.assertContains(detail_response, "Import Persons")
        self.assertContains(
            detail_response,
            f"{reverse('plugins:netbox_smartlock:accessrequestperson_bulk_import')}?request={access_request.pk}",
        )

        send_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_send", kwargs={"pk": access_request.pk})
        )
        self.assertEqual(send_response.status_code, 302)
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_SUBMITTED)
        self.assertTrue(
            self.AccessRequestHistory.objects.filter(
                request=access_request,
            action=self.AccessRequestHistory.ACTION_SUBMIT,
            ).exists()
        )

    def test_detail_hides_person_add_import_when_guest_lacks_add_permission(self):
        access_request = self.make_request(name="No Person Add Permission")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change"])
        self.grant_object_permission(self.AccessRequestPerson, ["view"])

        response = self.client.get(access_request.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Add Person")
        self.assertNotContains(response, "Import Persons")
        self.assertNotContains(response, reverse("plugins:netbox_smartlock:accessrequestperson_add"))
        self.assertNotContains(response, reverse("plugins:netbox_smartlock:accessrequestperson_bulk_import"))

    def test_guest_requires_object_change_permission_to_send_request(self):
        blocked_request = self.make_request(name="View Only Send Request")
        self.make_person(blocked_request)
        allowed_request = self.make_request(name="Object Change Send Request")
        self.make_person(
            allowed_request,
            identity_code="111122223334",
            full_name="Allowed Sender Person",
        )

        self.login()
        self.grant_object_permission_to_user(self.user, self.AccessRequest, ["view"])
        self.grant_object_permission_to_user(
            self.user,
            self.AccessRequest,
            ["change"],
            name_prefix="send-allowed",
            constraints={"name": allowed_request.name},
        )

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_send", kwargs={"pk": blocked_request.pk})
        )
        blocked_request.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_request.status, self.AccessRequest.STATUS_DRAFT)

        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_send", kwargs={"pk": allowed_request.pk})
        )
        allowed_request.refresh_from_db()

        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_request.status, self.AccessRequest.STATUS_SUBMITTED)

    def test_admin_cannot_send_guest_request(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        other_user = get_user_model().objects.create_user(
            username="send-owner",
            password="test-password",
        )
        access_request = self.make_created_request(other_user, name="Admin Should Not Send")
        self.make_person(access_request)

        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change"])

        response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_send", kwargs={"pk": access_request.pk})
        )
        access_request.refresh_from_db()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_DRAFT)

    def test_access_request_table_export_and_api_serializers(self):
        request = self.make_request(name="Exported Request")
        person = self.make_person(request)
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])

        response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"), {"export": "table"})

        self.assertEqual(response.status_code, 200)
        csv_content = response.content.decode()
        rows = list(csv.DictReader(csv_content.splitlines()))
        self.assertIn("Exported Request", csv_content)
        self.assertTrue(rows)

        excel_response = self.client.get(
            reverse("plugins:netbox_smartlock:accessrequest_list"),
            {"accessrequest_export": "excel_report"},
        )
        self.assertEqual(excel_response.status_code, 200)
        self.assertEqual(
            excel_response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        openpyxl = import_module("openpyxl")
        workbook = openpyxl.load_workbook(BytesIO(excel_response.content))
        self.assertIn("Access Requests", workbook.sheetnames)
        self.assertIn(
            "Exported Request",
            [cell.value for cell in workbook["Access Requests"]["A"]],
        )

        request_serializer_class = self.serializer_class("AccessRequestSerializer")
        person_serializer_class = self.serializer_class("AccessRequestPersonSerializer")

        request_serializer = request_serializer_class(instance=request, context={"request": None})
        person_serializer = person_serializer_class(instance=person, context={"request": None})

        self.assertEqual(request_serializer.data["name"], "Exported Request")
        self.assertEqual(request_serializer.data["site"]["id"], self.site.pk)
        self.assertEqual(person_serializer.data["identity_code"], "111122223333")
        self.assertEqual(person_serializer.data["location"]["id"], self.location.pk)

    def test_access_request_excel_export_is_scoped_to_guest_creator(self):
        other_user = get_user_model().objects.create_user(
            username="other-export-guest",
            password="test-password",
        )
        own_request = self.make_created_request(self.user, name="Owned Export Request")
        other_request = self.make_created_request(other_user, name="Other Export Request")
        self.make_person(own_request, identity_code="111122223336", full_name="Owned Export Person")
        self.make_person(other_request, identity_code="111122223337", full_name="Other Export Person")

        self.login()
        self.grant_object_permission_to_user(self.user, self.AccessRequest, ["view"])

        response = self.client.get(
            reverse("plugins:netbox_smartlock:accessrequest_list"),
            {"accessrequest_export": "excel_report"},
        )

        self.assertEqual(response.status_code, 200)
        openpyxl = import_module("openpyxl")
        workbook = openpyxl.load_workbook(BytesIO(response.content))
        names = [cell.value for cell in workbook["Access Requests"]["A"]]

        self.assertIn("Owned Export Request", names)
        self.assertNotIn("Other Export Request", names)

    def test_guest_users_only_see_their_own_access_requests(self):
        other_user = get_user_model().objects.create_user(
            username="other-guest",
            password="test-password",
        )
        own_request = self.make_created_request(self.user, name="Owned Request")
        other_request = self.make_created_request(other_user, name="Other Guest Request")
        self.make_person(own_request, identity_code="111122223334", full_name="Owned Person")
        self.make_person(other_request, identity_code="111122223335", full_name="Other Person")

        for user in (self.user, other_user):
            self.grant_object_permission_to_user(user, self.AccessRequest, ["view", "add", "change", "delete"])
            self.grant_object_permission_to_user(user, self.AccessRequestPerson, ["view", "add", "change", "delete"])

        self.login()

        request_list_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"))
        person_list_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_list"))
        other_detail_response = self.client.get(other_request.get_absolute_url())
        other_person_edit_response = self.client.get(other_request.persons.first().get_edit_url())

        self.assertEqual(request_list_response.status_code, 200)
        self.assertContains(request_list_response, "Owned Request")
        self.assertNotContains(request_list_response, "Other Guest Request")
        self.assertEqual(person_list_response.status_code, 200)
        self.assertContains(person_list_response, "Owned Person")
        self.assertNotContains(person_list_response, "Other Person")
        self.assertIn(other_detail_response.status_code, (403, 404))
        self.assertIn(other_person_edit_response.status_code, (403, 404))

    def test_guest_cannot_add_person_to_another_guests_request(self):
        other_user = get_user_model().objects.create_user(
            username="other-guest-target",
            password="test-password",
        )
        self.make_created_request(self.user, name="Own Draft Target")
        other_request = self.make_created_request(other_user, name="Other Draft Target")

        self.login()
        self.grant_object_permission_to_user(self.user, self.AccessRequest, ["view"])
        self.grant_object_permission_to_user(self.user, self.AccessRequestPerson, ["view", "add", "change", "delete"])
        self.grant_object_permission_to_user(self.user, Location, ["view"])

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                ui_response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_add"),
                    {
                        "request": other_request.pk,
                        "identity_code": "121212121212",
                        "full_name": "Cross Scope UI",
                        "organization": "Partner Co",
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": self.location.pk,
                        "description": "Should be blocked",
                        "upload_files": json.dumps(self.pending_payload(media_root)),
                    },
                )

        api_response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:accessrequestperson-list"),
            data=json.dumps(
                {
                    "request_id": other_request.pk,
                    "identity_code": "131313131313",
                    "full_name": "Cross Scope API",
                    "organization": "Partner Co",
                    "title": "Technician",
                    "phone": "0987654321",
                    "location_id": self.location.pk,
                    "description": "Should be blocked",
                }
            ),
            content_type="application/json",
        )

        self.assertIn(ui_response.status_code, (200, 403))
        self.assertIn(api_response.status_code, (400, 403))
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code="121212121212").exists())
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code="131313131313").exists())

    def test_api_person_create_and_update_require_attachment(self):
        access_request = self.make_request(name="API Attachment Required")
        person_without_file = self.make_person(
            access_request,
            identity_code="141414141414",
            full_name="API Update No File",
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add", "change"])
        self.grant_object_permission(Location, ["view"])

        create_without_file_response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:accessrequestperson-list"),
            data=json.dumps(
                {
                    "request_id": access_request.pk,
                    "identity_code": "151515151515",
                    "full_name": "API Missing File",
                    "organization": "Partner Co",
                    "title": "Technician",
                    "phone": "0987654321",
                    "location_id": self.location.pk,
                    "description": "Should be blocked",
                }
            ),
            content_type="application/json",
        )
        update_without_file_response = self.client.patch(
            reverse(
                "plugins-api:netbox_smartlock-api:accessrequestperson-detail",
                kwargs={"pk": person_without_file.pk},
            ),
            data=json.dumps({"title": "No attachment update"}),
            content_type="application/json",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                create_with_file_response = self.client.post(
                    reverse("plugins-api:netbox_smartlock-api:accessrequestperson-list"),
                    data=json.dumps(
                        {
                            "request_id": access_request.pk,
                            "identity_code": "161616161616",
                            "full_name": "API With File",
                            "organization": "Partner Co",
                            "title": "Technician",
                            "phone": "0987654321",
                            "location_id": self.location.pk,
                            "description": "Allowed with attachment",
                            "upload_files": json.dumps(self.pending_payload(media_root, filename="api-access.png")),
                        }
                    ),
                    content_type="application/json",
                )

        self.assertEqual(create_without_file_response.status_code, 400)
        self.assertEqual(update_without_file_response.status_code, 400)
        self.assertEqual(create_with_file_response.status_code, 201, create_with_file_response.content.decode())
        created_person = self.AccessRequestPerson.objects.get(identity_code="161616161616")
        self.assertTrue(
            UploadedFile.objects.filter(
                model_name="accessrequestperson",
                object_id=created_person.pk,
                file_name="api-access.png",
            ).exists()
        )

    def test_access_request_bulk_import_view_creates_request(self):
        self.login()
        self.grant_object_permission(self.AccessRequest, ["add", "change"])
        for model in (Region, Site):
            self.grant_object_permission(model, ["view"])

        get_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_bulk_import"))

        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Access Request Bulk Import")

        post_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": "\n".join(
                    [
                        "name,expected_date,reason,region,site",
                        "Imported Visit,2026-06-05,Inspect smartlock,north-ui,dc-ui",
                    ]
                ),
            },
        )

        self.assertEqual(post_response.status_code, 302)
        access_request = self.AccessRequest.objects.get(name="Imported Visit")
        self.assertEqual(access_request.region, self.region)
        self.assertEqual(access_request.site, self.site)

    def test_admin_cannot_bulk_import_access_requests(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "add", "change"])
        for model in (Region, Site):
            self.grant_object_permission(model, ["view"])

        import_url = reverse("plugins:netbox_smartlock:accessrequest_bulk_import")
        get_response = self.client.get(import_url)
        post_response = self.client.post(
            import_url,
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": "\n".join(
                    [
                        "name,expected_date,reason,region,site",
                        "Admin Imported Visit,2026-06-05,Admin should not create,north-ui,dc-ui",
                    ]
                ),
            },
        )

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(self.AccessRequest.objects.filter(name="Admin Imported Visit").exists())

    def test_access_request_created_by_is_set_on_ui_and_import(self):
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "add", "change"])
        for model in (Region, Site):
            self.grant_object_permission(model, ["view"])

        add_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_add"),
            {
                "name": "Creator UI",
                "expected_date": "2026-06-06",
                "reason": "Track creator",
                "region": self.region.pk,
                "site": self.site.pk,
            },
        )
        self.assertEqual(add_response.status_code, 302)

        import_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": "\n".join(
                    [
                        "name,expected_date,reason,region,site",
                        "Creator Import,2026-06-06,Track imported creator,north-ui,dc-ui",
                    ]
                ),
            },
        )
        self.assertEqual(import_response.status_code, 302)

        self.assertEqual(self.AccessRequest.objects.get(name="Creator UI").created_by, self.user)
        self.assertEqual(self.AccessRequest.objects.get(name="Creator Import").created_by, self.user)

    def test_person_add_requires_attachment(self):
        access_request = self.make_request(name="Attachment Required")
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["add"])
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(Location, ["view"])

        response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_add"),
            {
                "request": access_request.pk,
                "identity_code": "222233334444",
                "full_name": "No Attachment",
                "organization": "Partner Co",
                "title": "Technician",
                "phone": "0987654321",
                "location": self.location.pk,
                "description": "Missing file",
                "upload_files": "[]",
            },
        )

        self.assertEqual(response.status_code, 200, response.get("Location", response.content.decode()))
        form = response.context.get("form")
        self.assertIn("upload_files", form.errors)

    def test_person_edit_cannot_remove_all_attachments(self):
        access_request = self.make_request(name="Attachment Retained")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add", "change"])
        self.grant_object_permission(Location, ["view"])

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                add_response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_add"),
                    {
                        "request": access_request.pk,
                        "identity_code": "222233334445",
                        "full_name": "Attachment Owner",
                        "organization": "Partner Co",
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": self.location.pk,
                        "description": "Initial file",
                        "upload_files": json.dumps(self.pending_payload(media_root, filename="retained.png")),
                    },
                )
                self.assertEqual(add_response.status_code, 302)
                person = self.AccessRequestPerson.objects.get(identity_code="222233334445")

                edit_response = self.client.post(
                    person.get_edit_url(),
                    {
                        "request": access_request.pk,
                        "identity_code": person.identity_code,
                        "full_name": person.full_name,
                        "organization": person.organization,
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": self.location.pk,
                        "description": "Remove all files",
                        "upload_files": "[]",
                    },
                )

        self.assertEqual(edit_response.status_code, 200)
        form = edit_response.context.get("form")
        self.assertIn("upload_files", form.errors)
        self.assertTrue(
            UploadedFile.objects.filter(
                model_name="accessrequestperson",
                object_id=person.pk,
                file_name="retained.png",
            ).exists()
        )

    def test_deleting_access_request_person_removes_uploaded_files(self):
        access_request = self.make_request(name="Delete Person File")
        person = self.make_person(
            access_request,
            identity_code="222233334446",
            full_name="Delete File Person",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                uploaded_file = UploadedFile(
                    file_name="delete-person.png",
                    content_type=ContentType.objects.get_for_model(person, for_concrete_model=False),
                    object_id=person.pk,
                    model_name="accessrequestperson",
                )
                uploaded_file.file.save(
                    "uploads/accessrequestperson/delete-person.png",
                    ContentFile(b"delete-person"),
                    save=True,
                )
                storage_path = Path(uploaded_file.file.path)

                person.delete()

                self.assertFalse(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
                self.assertFalse(storage_path.exists())

    def test_deleting_access_request_cascade_removes_person_uploaded_files(self):
        access_request = self.make_request(name="Cascade Delete File")
        person = self.make_person(
            access_request,
            identity_code="222233334447",
            full_name="Cascade File Person",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                uploaded_file = UploadedFile(
                    file_name="cascade-person.png",
                    content_type=ContentType.objects.get_for_model(person, for_concrete_model=False),
                    object_id=person.pk,
                    model_name="accessrequestperson",
                )
                uploaded_file.file.save(
                    "uploads/accessrequestperson/cascade-person.png",
                    ContentFile(b"cascade-person"),
                    save=True,
                )
                storage_path = Path(uploaded_file.file.path)

                access_request.delete()

                self.assertFalse(UploadedFile.objects.filter(pk=uploaded_file.pk).exists())
                self.assertFalse(storage_path.exists())

    def test_delete_temp_file_view_rejects_paths_outside_upload_tmp(self):
        self.login()

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"):
                outside_dir = Path(media_root) / "uploads" / "tmp_evil"
                outside_dir.mkdir(parents=True)
                outside_file = outside_dir / "outside.png"
                outside_file.write_bytes(b"outside")

                request = RequestFactory().post(
                    "/plugins/upload-file/delete_temp_file/",
                    {
                        "file_name": "outside.png",
                        "path": "/media/uploads/tmp_evil/outside.png",
                    },
                )
                request.user = self.user

                response = delete_temp_file_view(request)

                self.assertEqual(response.status_code, 400)
                self.assertTrue(outside_file.exists())

                inside_dir = Path(media_root) / "uploads" / "tmp"
                inside_dir.mkdir(parents=True, exist_ok=True)
                inside_file = inside_dir / "inside.png"
                inside_file.write_bytes(b"inside")

                valid_request = RequestFactory().post(
                    "/plugins/upload-file/delete_temp_file/",
                    {
                        "file_name": "inside.png",
                        "path": "/media/uploads/tmp/inside.png",
                    },
                )
                valid_request.user = self.user

                valid_response = delete_temp_file_view(valid_request)

                self.assertEqual(valid_response.status_code, 200)
                self.assertFalse(inside_file.exists())

    def test_person_bulk_import_without_attachment_is_blocked(self):
        access_request = self.make_request(name="Import Request")
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["add", "change"])
        for model in (self.AccessRequest, Location):
            self.grant_object_permission(model, ["view"])

        response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": "\n".join(
                    [
                        "request,identity_code,full_name,organization,title,phone,location,description",
                        f"{access_request.pk},333344445555,Imported Person,Partner Co,Engineer,0911111111,{self.location.pk},Imported row",
                    ]
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code="333344445555").exists())

    def test_person_bulk_import_with_attachment_creates_person_and_uploaded_file(self):
        access_request = self.make_request(name="Import With Attachment")
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["add", "change"])
        for model in (self.AccessRequest, Location):
            self.grant_object_permission(model, ["view"])

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                payload = json.dumps(self.pending_payload(media_root, filename="bulk-access.png"))
                response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_bulk_import"),
                    {
                        "format": ImportFormatChoices.CSV,
                        "csv_delimiter": CSVDelimiterChoices.COMMA,
                        "data": self.csv_text(
                            [
                                "request",
                                "identity_code",
                                "full_name",
                                "organization",
                                "title",
                                "phone",
                                "location",
                                "description",
                                "upload_files",
                            ],
                            {
                                "request": access_request.pk,
                                "identity_code": "333344445556",
                                "full_name": "Imported Attached Person",
                                "organization": "Partner Co",
                                "title": "Engineer",
                                "phone": "0911111111",
                                "location": self.location.pk,
                                "description": "Imported row",
                                "upload_files": payload,
                            },
                        ),
                    },
                )

        self.assertEqual(response.status_code, 302, response.content.decode())
        person = self.AccessRequestPerson.objects.get(identity_code="333344445556")
        self.assertEqual(person.request, access_request)
        self.assertTrue(
            UploadedFile.objects.filter(
                model_name="accessrequestperson",
                object_id=person.pk,
                file_name="bulk-access.png",
            ).exists()
        )

    def test_person_detail_tab_scoped_import_defaults_request(self):
        access_request = self.make_request(name="Scoped Person Import")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add", "change"])
        self.grant_object_permission(Location, ["view"])

        detail_response = self.client.get(access_request.get_absolute_url())
        self.assertContains(detail_response, "Import Persons")
        self.assertContains(
            detail_response,
            f"{reverse('plugins:netbox_smartlock:accessrequestperson_bulk_import')}?request={access_request.pk}",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                payload = json.dumps(self.pending_payload(media_root, filename="scoped-import.png"))
                import_response = self.client.post(
                    f"{reverse('plugins:netbox_smartlock:accessrequestperson_bulk_import')}?request={access_request.pk}",
                    {
                        "format": ImportFormatChoices.CSV,
                        "csv_delimiter": CSVDelimiterChoices.COMMA,
                        "data": self.csv_text(
                            [
                                "identity_code",
                                "full_name",
                                "organization",
                                "title",
                                "phone",
                                "location",
                                "description",
                                "upload_files",
                            ],
                            {
                                "identity_code": "333344445557",
                                "full_name": "Scoped Imported Person",
                                "organization": "Partner Co",
                                "title": "Engineer",
                                "phone": "0911111111",
                                "location": self.location.pk,
                                "description": "Scoped imported row",
                                "upload_files": payload,
                            },
                        ),
                    },
                )

        self.assertEqual(import_response.status_code, 302, import_response.content.decode())
        person = self.AccessRequestPerson.objects.get(identity_code="333344445557")
        self.assertEqual(person.request, access_request)
        self.assertTrue(
            UploadedFile.objects.filter(
                model_name="accessrequestperson",
                object_id=person.pk,
                file_name="scoped-import.png",
            ).exists()
        )

    def test_person_add_edit_import_blocked_and_delete_allowed_when_parent_is_accepted(self):
        access_request = self.make_request(name="Accepted Person Parent", status=self.AccessRequest.STATUS_ACCEPTED)
        person = self.make_person(
            access_request,
            identity_code="444455556666",
            full_name="Verified Accepted Parent",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add", "change", "delete"])
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(Location, ["view"])

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                add_response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_add"),
                    {
                        "request": access_request.pk,
                        "identity_code": "444455556667",
                        "full_name": "Blocked New Person",
                        "organization": "Partner Co",
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": self.location.pk,
                        "description": "Should be blocked",
                        "upload_files": json.dumps(self.pending_payload(media_root)),
                    },
                )

        edit_response = self.client.get(person.get_edit_url())
        delete_response = self.client.get(person.get_delete_url())
        import_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_import"),
            {
                "format": ImportFormatChoices.CSV,
                "csv_delimiter": CSVDelimiterChoices.COMMA,
                "data": "\n".join(
                    [
                        "request,identity_code,full_name,organization,title,phone,location,description",
                        f"{access_request.pk},444455556668,Blocked Import,Partner Co,Engineer,0911111111,{self.location.pk},Imported row",
                    ]
                ),
            },
        )

        self.assertEqual(add_response.status_code, 200)
        add_form = add_response.context.get("form")
        self.assertIn("request", add_form.errors)
        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(import_response.status_code, 200)
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code="444455556667").exists())
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code="444455556668").exists())

    def test_person_delete_blocked_when_parent_is_completed(self):
        access_request = self.make_request(name="Completed Person Parent", status=self.AccessRequest.STATUS_COMPLETED)
        person = self.make_person(
            access_request,
            identity_code="444455556669",
            full_name="Completed Parent Person",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["view", "delete"])

        delete_response = self.client.get(person.get_delete_url())

        self.assertEqual(delete_response.status_code, 403)

    def test_direct_guest_actions_are_blocked_by_status(self):
        self.login()
        for model in (self.AccessRequest, self.AccessRequestPerson):
            self.grant_object_permission(model, ["view", "change", "delete"])

        accepted_request = self.make_request(name="Accepted Request", status=self.AccessRequest.STATUS_ACCEPTED)
        completed_request = self.make_request(name="Completed Request", status=self.AccessRequest.STATUS_COMPLETED)
        pending_person = self.make_person(
            accepted_request,
            identity_code="555566667777",
            full_name="Pending Accepted",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )
        verified_person = self.make_person(accepted_request, verify_status=self.AccessRequestPerson.VERIFY_VALID)

        edit_response = self.client.get(accepted_request.get_edit_url())
        accepted_delete_response = self.client.get(accepted_request.get_delete_url())
        delete_response = self.client.get(completed_request.get_delete_url())
        pending_person_edit_response = self.client.get(pending_person.get_edit_url())
        pending_person_delete_response = self.client.get(pending_person.get_delete_url())
        person_edit_response = self.client.get(verified_person.get_edit_url())
        person_delete_response = self.client.get(verified_person.get_delete_url())

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(accepted_delete_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertEqual(pending_person_edit_response.status_code, 403)
        self.assertEqual(pending_person_delete_response.status_code, 200)
        self.assertEqual(person_edit_response.status_code, 403)
        self.assertEqual(person_delete_response.status_code, 200)

    def test_bulk_guest_actions_are_blocked_by_status(self):
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change", "delete"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "change", "delete"])

        accepted_request = self.make_request(name="Accepted Bulk", status=self.AccessRequest.STATUS_ACCEPTED)
        completed_request = self.make_request(name="Completed Bulk", status=self.AccessRequest.STATUS_COMPLETED)
        pending_person = self.make_person(
            accepted_request,
            identity_code="666677778888",
            full_name="Pending Bulk",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )
        verified_person = self.make_person(accepted_request, verify_status=self.AccessRequestPerson.VERIFY_VALID)

        bulk_edit_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_edit"),
            {"pk": [accepted_request.pk], "status": self.AccessRequest.STATUS_REJECTED, "_apply": "Apply"},
        )
        bulk_rename_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_rename"),
            {"pk": [accepted_request.pk], "find": "Accepted", "replace": "Renamed", "_apply": "Apply"},
        )
        bulk_delete_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_delete"),
            {"pk": [completed_request.pk], "confirm": "true"},
        )
        accepted_bulk_delete_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_delete"),
            {"pk": [accepted_request.pk], "confirm": "true"},
        )
        pending_person_bulk_edit_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_edit"),
            {"pk": [pending_person.pk], "title": "Blocked", "_apply": "Apply"},
        )
        pending_person_bulk_delete_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_delete"),
            {"pk": [pending_person.pk], "_confirm": "true", "confirm": "true"},
        )
        person_bulk_edit_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_edit"),
            {"pk": [verified_person.pk], "title": "Blocked", "_apply": "Apply"},
        )
        person_bulk_delete_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_delete"),
            {"pk": [verified_person.pk], "_confirm": "true", "confirm": "true"},
        )

        self.assertEqual(bulk_edit_response.status_code, 403)
        self.assertEqual(bulk_rename_response.status_code, 403)
        self.assertEqual(bulk_delete_response.status_code, 403)
        self.assertEqual(accepted_bulk_delete_response.status_code, 403)
        self.assertEqual(pending_person_bulk_edit_response.status_code, 403)
        self.assertEqual(pending_person_bulk_delete_response.status_code, 302)
        self.assertEqual(person_bulk_edit_response.status_code, 403)
        self.assertEqual(person_bulk_delete_response.status_code, 302)

    def test_access_request_person_list_has_netbox_bulk_action_urls(self):
        self.login()
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add", "change", "delete"])

        response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_list"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('href="None"', content)
        self.assertNotIn('formaction="None"', content)
        self.assertNotIn("/plugins/smartlock/access-request-persons/None", content)
        self.assertIn("/plugins/smartlock/access-request-persons/import/", content)
        self.assertIn("/plugins/smartlock/access-request-persons/edit/", content)
        self.assertIn("/plugins/smartlock/access-request-persons/delete/", content)

    def test_access_request_person_navigation_is_request_scoped(self):
        navigation = import_module("netbox_smartlock.navigation")

        security_items = []
        for group in navigation.menu.groups:
            if group.label == "Security Control":
                security_items = list(group.items)
                break

        self.assertEqual([item.link_text for item in security_items], ["Access Requests"])
        self.assertFalse(
            any(
                getattr(button, "link", "") == "plugins:netbox_smartlock:accessrequestperson_add"
                for item in security_items
                for button in getattr(item, "buttons", ())
            )
        )

    def test_list_row_actions_hide_edit_delete_when_workflow_state_is_readonly(self):
        draft_request = self.make_request(name="Draft Row Actions")
        accepted_request = self.make_request(name="Accepted Row Actions", status=self.AccessRequest.STATUS_ACCEPTED)
        editable_person = self.make_person(
            draft_request,
            identity_code="989898989898",
            full_name="Editable Row Person",
        )
        accepted_person = self.make_person(
            accepted_request,
            identity_code="979797979797",
            full_name="Accepted Row Person",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change", "delete"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "change", "delete"])

        request_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"))
        person_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_list"))

        self.assertEqual(request_response.status_code, 200)
        request_content = request_response.content.decode()
        self.assertIn(draft_request.get_edit_url(), request_content)
        self.assertIn(draft_request.get_delete_url(), request_content)
        self.assertNotIn(accepted_request.get_edit_url(), request_content)
        self.assertNotIn(accepted_request.get_delete_url(), request_content)

        self.assertEqual(person_response.status_code, 200)
        person_content = person_response.content.decode()
        self.assertIn(editable_person.get_edit_url(), person_content)
        self.assertIn(editable_person.get_delete_url(), person_content)
        self.assertNotIn(accepted_person.get_edit_url(), person_content)
        self.assertIn(accepted_person.get_delete_url(), person_content)

    def test_rejected_verified_person_can_be_reworked_from_ui(self):
        rejected_request = self.make_request(name="Rejected UI Rework", status=self.AccessRequest.STATUS_REJECTED)
        verified_person = self.make_person(
            rejected_request,
            identity_code="969696969697",
            full_name="Rejected Verified Person",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change", "delete"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "change", "delete"])

        request_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"))
        person_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_list"))
        person_edit_response = self.client.get(verified_person.get_edit_url())
        person_delete_response = self.client.get(verified_person.get_delete_url())

        self.assertEqual(request_response.status_code, 200)
        request_content = request_response.content.decode()
        self.assertIn(rejected_request.get_edit_url(), request_content)
        self.assertIn(rejected_request.get_delete_url(), request_content)

        self.assertEqual(person_response.status_code, 200)
        person_content = person_response.content.decode()
        self.assertIn(verified_person.get_edit_url(), person_content)
        self.assertIn(verified_person.get_delete_url(), person_content)
        self.assertEqual(person_edit_response.status_code, 200)
        self.assertEqual(person_delete_response.status_code, 200)

    def test_admin_role_cannot_use_generic_crud_actions(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        access_request = self.make_request(name="Admin Generic CRUD")
        person = self.make_person(access_request)

        self.login()
        for model in (self.AccessRequest, self.AccessRequestPerson):
            self.grant_object_permission(model, ["view", "add", "change", "delete"])
        self.grant_object_permission(Location, ["view"])

        detail_response = self.client.get(access_request.get_absolute_url())
        request_list_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_list"))
        person_list_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_list"))

        self.assertEqual(detail_response.status_code, 200)
        detail_content = detail_response.content.decode()
        self.assertNotIn(access_request.get_edit_url(), detail_content)
        self.assertNotIn(access_request.get_delete_url(), detail_content)
        self.assertNotIn(reverse("plugins:netbox_smartlock:accessrequestperson_add"), detail_content)

        self.assertEqual(request_list_response.status_code, 200)
        request_list_content = request_list_response.content.decode()
        self.assertNotIn(access_request.get_edit_url(), request_list_content)
        self.assertNotIn(access_request.get_delete_url(), request_list_content)

        self.assertEqual(person_list_response.status_code, 200)
        person_list_content = person_list_response.content.decode()
        self.assertNotIn(person.get_edit_url(), person_list_content)
        self.assertNotIn(person.get_delete_url(), person_list_content)

        self.assertEqual(self.client.get(access_request.get_edit_url()).status_code, 403)
        self.assertEqual(self.client.get(access_request.get_delete_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_add")).status_code, 403)
        self.assertEqual(self.client.get(person.get_edit_url()).status_code, 403)
        self.assertEqual(self.client.get(person.get_delete_url()).status_code, 403)

        api_request_detail = reverse(
            "plugins-api:netbox_smartlock-api:accessrequest-detail",
            kwargs={"pk": access_request.pk},
        )
        api_person_detail = reverse(
            "plugins-api:netbox_smartlock-api:accessrequestperson-detail",
            kwargs={"pk": person.pk},
        )
        api_request_patch_response = self.client.patch(
            api_request_detail,
            data=json.dumps({"reason": "Admin should not update generic fields"}),
            content_type="application/json",
        )
        api_person_patch_response = self.client.patch(
            api_person_detail,
            data=json.dumps({"title": "Admin should not update generic fields"}),
            content_type="application/json",
        )
        api_request_delete_response = self.client.delete(api_request_detail)
        api_person_delete_response = self.client.delete(api_person_detail)

        self.assertEqual(api_request_patch_response.status_code, 403)
        self.assertEqual(api_person_patch_response.status_code, 403)
        self.assertEqual(api_request_delete_response.status_code, 403)
        self.assertEqual(api_person_delete_response.status_code, 403)

    def test_access_request_detail_uses_business_tabs_with_changelog(self):
        access_request = self.make_request(name="Tabbed Detail")
        self.make_person(access_request, identity_code="969696969696", full_name="Tabbed Person")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(self.AccessRequestPerson, ["view"])

        response = self.client.get(access_request.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        for expected in (
            "access-request-detail-tab",
            "access-request-history-tab",
            "access-request-changelog-tab",
            "access-request-persons-tab",
            "Username",
            "Full Name",
            "Type",
            "Object",
            "Request ID",
            "Phiếu yêu cầu ra vào",
            "Lịch sử yêu cầu",
            "Nhật ký thay đổi",
            "Đối tượng",
        ):
            self.assertContains(response, expected)

    def test_guest_edit_forms_render_cancel_confirmation(self):
        access_request = self.make_request(name="Cancel Confirm")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "add", "change"])
        self.grant_object_permission(self.AccessRequestPerson, ["add"])
        self.grant_object_permission(Location, ["view"])

        request_add_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequest_add"))
        request_edit_response = self.client.get(access_request.get_edit_url())
        person_add_response = self.client.get(
            reverse("plugins:netbox_smartlock:accessrequestperson_add"),
            {"request": access_request.pk},
        )

        for response in (request_add_response, request_edit_response, person_add_response):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "smartlock-cancel-confirm-modal")
            self.assertContains(response, "data-smartlock-cancel-confirm")

    def test_access_request_region_site_and_person_location_respect_netbox_object_permissions(self):
        restricted_location = Location.objects.create(
            name="Restricted Room UI",
            slug="restricted-room-ui",
            site=self.site,
        )
        access_request = self.make_request(name="Scoped DCIM")

        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "add", "change"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "add"])
        self.grant_object_permission_to_user(
            self.user,
            Region,
            ["view"],
            name_prefix="scope",
            constraints={"slug": self.region.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Site,
            ["view"],
            name_prefix="scope",
            constraints={"slug": self.site.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Location,
            ["view"],
            name_prefix="scope",
            constraints={"slug": self.location.slug},
        )

        request_ui_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_add"),
            {
                "name": "Out Of Scope DCIM UI",
                "expected_date": "2026-06-08",
                "reason": "Should reject out-of-scope DCIM objects",
                "region": self.other_region.pk,
                "site": self.other_site.pk,
            },
        )
        request_api_response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:accessrequest-list"),
            data=json.dumps(
                {
                    "name": "Out Of Scope DCIM API",
                    "expected_date": "2026-06-08",
                    "reason": "Should reject out-of-scope DCIM objects",
                    "region_id": self.other_region.pk,
                    "site_id": self.other_site.pk,
                }
            ),
            content_type="application/json",
        )

        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                person_ui_response = self.client.post(
                    reverse("plugins:netbox_smartlock:accessrequestperson_add"),
                    {
                        "request": access_request.pk,
                        "identity_code": "939393939393",
                        "full_name": "Out Of Scope Location UI",
                        "organization": "Partner Co",
                        "title": "Technician",
                        "phone": "0987654321",
                        "location": restricted_location.pk,
                        "description": "Should be blocked by object permission",
                        "upload_files": json.dumps(self.pending_payload(media_root)),
                    },
                )
        person_api_response = self.client.post(
            reverse("plugins-api:netbox_smartlock-api:accessrequestperson-list"),
            data=json.dumps(
                {
                    "request_id": access_request.pk,
                    "identity_code": "949494949494",
                    "full_name": "Out Of Scope Location API",
                    "organization": "Partner Co",
                    "title": "Technician",
                    "phone": "0987654321",
                    "location_id": restricted_location.pk,
                    "description": "Should be blocked by object permission",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(request_ui_response.status_code, 200)
        self.assertEqual(request_api_response.status_code, 400)
        self.assertEqual(person_ui_response.status_code, 200)
        self.assertEqual(person_api_response.status_code, 400)
        self.assertFalse(self.AccessRequest.objects.filter(name__startswith="Out Of Scope DCIM").exists())
        self.assertFalse(self.AccessRequestPerson.objects.filter(identity_code__in=("939393939393", "949494949494")).exists())

    def test_bulk_edit_dcim_fields_respect_object_permissions_and_request_site_scope(self):
        access_request = self.make_request(name="Bulk Scope")
        person = self.make_person(
            access_request,
            identity_code="949494949495",
            full_name="Bulk Scope Person",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change"])
        self.grant_object_permission(self.AccessRequestPerson, ["view", "change"])
        self.grant_object_permission_to_user(
            self.user,
            Region,
            ["view"],
            name_prefix="bulk-scope",
            constraints={"slug": self.region.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Site,
            ["view"],
            name_prefix="bulk-scope",
            constraints={"slug": self.site.slug},
        )
        self.grant_object_permission_to_user(
            self.user,
            Location,
            ["view"],
            name_prefix="bulk-scope",
            constraints={"slug": self.location.slug},
        )

        request_bulk_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_bulk_edit"),
            {
                "pk": [access_request.pk],
                "region": self.other_region.pk,
                "site": self.other_site.pk,
                "_apply": "Apply",
            },
        )
        person_bulk_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_bulk_edit"),
            {
                "pk": [person.pk],
                "location": self.other_location.pk,
                "_apply": "Apply",
            },
        )

        access_request.refresh_from_db()
        person.refresh_from_db()
        self.assertEqual(request_bulk_response.status_code, 200)
        self.assertEqual(person_bulk_response.status_code, 200)
        self.assertEqual(access_request.region, self.region)
        self.assertEqual(access_request.site, self.site)
        self.assertEqual(person.location, self.location)

    def test_person_add_location_widget_is_scoped_to_selected_request_site(self):
        access_request = self.make_request(name="Location Widget Scope")
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])
        self.grant_object_permission(self.AccessRequestPerson, ["add"])
        self.grant_object_permission(Location, ["view"])

        unscoped_response = self.client.get(reverse("plugins:netbox_smartlock:accessrequestperson_add"))
        scoped_response = self.client.get(
            reverse("plugins:netbox_smartlock:accessrequestperson_add"),
            {"request": access_request.pk},
        )

        self.assertEqual(unscoped_response.status_code, 200)
        self.assertContains(unscoped_response, "data-smartlock-location-scope")
        self.assertContains(unscoped_response, "data-smartlock-request-field=\"id_request\"")

        self.assertEqual(scoped_response.status_code, 200)
        scoped_content = scoped_response.content.decode()
        self.assertIn("&quot;queryParam&quot;:&quot;site_id&quot;", scoped_content)
        self.assertIn(f"&quot;queryValue&quot;:[&quot;{self.site.pk}&quot;]", scoped_content)
        self.assertNotIn(f"&quot;queryValue&quot;:[&quot;{self.other_site.pk}&quot;]", scoped_content)


    def test_guest_forms_do_not_expose_workflow_status_fields(self):
        form_class = getattr(import_module("netbox_smartlock.forms"), "AccessRequestBulkEditForm")
        request_form_class = getattr(import_module("netbox_smartlock.forms"), "AccessRequestForm")
        request_import_form_class = getattr(import_module("netbox_smartlock.forms"), "AccessRequestImportForm")
        person_form_class = getattr(import_module("netbox_smartlock.forms"), "AccessRequestPersonForm")
        person_import_form_class = getattr(import_module("netbox_smartlock.forms"), "AccessRequestPersonImportForm")

        self.assertNotIn("status", request_form_class.base_fields)
        self.assertNotIn("status", form_class.base_fields)
        self.assertNotIn("status", request_import_form_class.base_fields)
        self.assertNotIn("verify_status", person_form_class.base_fields)
        self.assertNotIn("verify_status", person_import_form_class.base_fields)
        self.assertNotIn("access_status", person_form_class.base_fields)

    def test_api_workflow_status_fields_are_read_only(self):
        request_serializer_class = self.serializer_class("AccessRequestSerializer")
        person_serializer_class = self.serializer_class("AccessRequestPersonSerializer")
        access_request = self.make_request(name="Read Only API")
        person = self.make_person(access_request)

        request_serializer = request_serializer_class(
            instance=access_request,
            data={
                "name": access_request.name,
                "expected_date": "2026-06-02",
                "reason": access_request.reason,
                "status": self.AccessRequest.STATUS_ACCEPTED,
                "region_id": self.region.pk,
                "site_id": self.site.pk,
            },
            partial=True,
            context={"request": None},
        )
        person_serializer = person_serializer_class(
            instance=person,
            data={
                "verify_status": self.AccessRequestPerson.VERIFY_VALID,
                "access_status": self.AccessRequestPerson.ACCESS_IN,
            },
            partial=True,
            context={"request": None},
        )

        self.assertTrue(request_serializer.is_valid(), request_serializer.errors)
        self.assertNotIn("status", request_serializer.validated_data)
        self.assertTrue(person_serializer.is_valid(), person_serializer.errors)
        self.assertNotIn("verify_status", person_serializer.validated_data)
        self.assertNotIn("access_status", person_serializer.validated_data)

    def test_api_blocks_guest_field_updates_when_workflow_state_is_readonly(self):
        request_serializer_class = self.serializer_class("AccessRequestSerializer")
        person_serializer_class = self.serializer_class("AccessRequestPersonSerializer")
        accepted_request = self.make_request(name="Accepted API", status=self.AccessRequest.STATUS_ACCEPTED)
        pending_person = self.make_person(
            accepted_request,
            identity_code="777788889999",
            full_name="Pending API",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )

        request_serializer = request_serializer_class(
            instance=accepted_request,
            data={"reason": "Changed through API"},
            partial=True,
            context={"request": None},
        )
        person_update_serializer = person_serializer_class(
            instance=pending_person,
            data={"title": "Changed through API"},
            partial=True,
            context={"request": None},
        )
        person_create_serializer = person_serializer_class(
            data={
                "request_id": accepted_request.pk,
                "identity_code": "777788889990",
                "full_name": "Created Through API",
                "organization": "Partner Co",
                "title": "Technician",
                "phone": "0987654321",
                "location_id": self.location.pk,
                "description": "Should be blocked",
            },
            context={"request": None},
        )

        self.assertFalse(request_serializer.is_valid())
        self.assertIn("status", request_serializer.errors)
        self.assertFalse(person_update_serializer.is_valid())
        self.assertIn("request", person_update_serializer.errors)
        self.assertFalse(person_create_serializer.is_valid())
        self.assertIn("request", person_create_serializer.errors)

    def test_accept_requires_all_persons_to_be_verified_valid(self):
        access_request = self.make_request(name="Pending Person Decision", status=self.AccessRequest.STATUS_CONFIRMED)
        self.make_person(
            access_request,
            identity_code="888899990000",
            full_name="Still Pending",
            verify_status=self.AccessRequestPerson.VERIFY_PENDING,
        )

        with self.assertRaises(ValidationError):
            access_request.accept(user=self.user)

        access_request.refresh_from_db()
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_CONFIRMED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_ui_workflow_actions(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        access_request = self.make_request(name="Admin UI Flow")
        person = self.make_person(access_request)
        access_request.submit(user=self.user)

        self.login()
        for model in (self.AccessRequest, self.AccessRequestPerson):
            self.grant_object_permission(model, ["view", "change"])

        detail_response = self.client.get(access_request.get_absolute_url())
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Confirm")
        self.assertNotIn('href="None"', detail_response.content.decode())
        self.assertNotIn('formaction="None"', detail_response.content.decode())

        confirm_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_confirm", kwargs={"pk": access_request.pk})
        )
        self.assertEqual(confirm_response.status_code, 302)
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_CONFIRMED)

        valid_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_verify_valid", kwargs={"pk": person.pk}),
            {"return_url": access_request.get_absolute_url()},
        )
        self.assertEqual(valid_response.status_code, 302)
        person.refresh_from_db()
        self.assertEqual(person.verify_status, self.AccessRequestPerson.VERIFY_VALID)

        accept_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_accept", kwargs={"pk": access_request.pk})
        )
        self.assertEqual(accept_response.status_code, 302)
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_ACCEPTED)

        check_in_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_in", kwargs={"pk": person.pk}),
            {"return_url": access_request.get_absolute_url()},
        )
        self.assertEqual(check_in_response.status_code, 302)
        person.refresh_from_db()
        self.assertEqual(person.access_status, self.AccessRequestPerson.ACCESS_IN)

        check_out_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_out", kwargs={"pk": person.pk}),
            {"return_url": access_request.get_absolute_url()},
        )
        self.assertEqual(check_out_response.status_code, 302)
        person.refresh_from_db()
        self.assertEqual(person.access_status, self.AccessRequestPerson.ACCESS_OUT)

        complete_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_complete", kwargs={"pk": access_request.pk})
        )
        self.assertEqual(complete_response.status_code, 302)
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_COMPLETED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_workflow_requires_netbox_change_permission_and_complete_uses_modal(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        access_request = self.make_request(name="Change Permission Flow", status=self.AccessRequest.STATUS_ACCEPTED)
        self.make_person(
            access_request,
            identity_code="999900001111",
            full_name="Verified Admin Person",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_complete", kwargs={"pk": access_request.pk})
        )
        access_request.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_ACCEPTED)

        self.grant_object_permission(self.AccessRequest, ["change"])
        detail_response = self.client.get(access_request.get_absolute_url())

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "complete-request-modal")
        self.assertContains(detail_response, "Complete Access Request")
        self.assertContains(detail_response, "data-bs-target=\"#complete-request-modal\"")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_request_workflow_requires_object_change_permission(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        self.login()
        self.grant_object_permission_to_user(self.user, self.AccessRequest, ["view"], name_prefix="workflow-view")

        def make_workflow_request(name, status, identity_code, verify_status=None):
            access_request = self.make_request(name=name, status=status)
            self.make_person(
                access_request,
                identity_code=identity_code,
                full_name=f"{name} Person",
                verify_status=verify_status or self.AccessRequestPerson.VERIFY_PENDING,
            )
            return access_request

        def grant_change(access_request, prefix):
            self.grant_object_permission_to_user(
                self.user,
                self.AccessRequest,
                ["change"],
                name_prefix=prefix,
                constraints={"name": access_request.name},
            )

        blocked_confirm = make_workflow_request(
            "Blocked Confirm Scope",
            self.AccessRequest.STATUS_SUBMITTED,
            "171717171700",
        )
        allowed_confirm = make_workflow_request(
            "Allowed Confirm Scope",
            self.AccessRequest.STATUS_SUBMITTED,
            "171717171701",
        )
        grant_change(allowed_confirm, "workflow-confirm")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_confirm", kwargs={"pk": blocked_confirm.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_confirm", kwargs={"pk": allowed_confirm.pk})
        )
        blocked_confirm.refresh_from_db()
        allowed_confirm.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_confirm.status, self.AccessRequest.STATUS_SUBMITTED)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_confirm.status, self.AccessRequest.STATUS_CONFIRMED)

        blocked_reject = make_workflow_request(
            "Blocked Reject Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "171717171702",
        )
        allowed_reject = make_workflow_request(
            "Allowed Reject Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "171717171703",
        )
        grant_change(allowed_reject, "workflow-reject")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_reject", kwargs={"pk": blocked_reject.pk}),
            {"description": "Reject reason"},
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_reject", kwargs={"pk": allowed_reject.pk}),
            {"description": "Reject reason"},
        )
        blocked_reject.refresh_from_db()
        allowed_reject.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_reject.status, self.AccessRequest.STATUS_CONFIRMED)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_reject.status, self.AccessRequest.STATUS_REJECTED)

        blocked_accept = make_workflow_request(
            "Blocked Accept Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "171717171704",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        allowed_accept = make_workflow_request(
            "Allowed Accept Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "171717171705",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        grant_change(allowed_accept, "workflow-accept")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_accept", kwargs={"pk": blocked_accept.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_accept", kwargs={"pk": allowed_accept.pk})
        )
        blocked_accept.refresh_from_db()
        allowed_accept.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_accept.status, self.AccessRequest.STATUS_CONFIRMED)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_accept.status, self.AccessRequest.STATUS_ACCEPTED)

        blocked_complete = make_workflow_request(
            "Blocked Complete Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "171717171706",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        allowed_complete = make_workflow_request(
            "Allowed Complete Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "171717171707",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        grant_change(allowed_complete, "workflow-complete")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_complete", kwargs={"pk": blocked_complete.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_complete", kwargs={"pk": allowed_complete.pk})
        )
        blocked_complete.refresh_from_db()
        allowed_complete.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_complete.status, self.AccessRequest.STATUS_ACCEPTED)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_complete.status, self.AccessRequest.STATUS_COMPLETED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_person_workflow_requires_object_change_permission(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        self.login()
        self.grant_object_permission_to_user(self.user, self.AccessRequest, ["view"], name_prefix="person-workflow-request-view")
        self.grant_object_permission_to_user(self.user, self.AccessRequestPerson, ["view"], name_prefix="person-workflow-view")

        def make_workflow_person(name, status, identity_code, *, verify_status=None, access_status=None):
            access_request = self.make_request(name=name, status=status)
            return self.make_person(
                access_request,
                identity_code=identity_code,
                full_name=f"{name} Person",
                verify_status=verify_status or self.AccessRequestPerson.VERIFY_PENDING,
                access_status=access_status or self.AccessRequestPerson.ACCESS_OUT,
            )

        def grant_change(person, prefix):
            self.grant_object_permission_to_user(
                self.user,
                self.AccessRequestPerson,
                ["change"],
                name_prefix=prefix,
                constraints={"identity_code": person.identity_code},
            )

        blocked_valid = make_workflow_person(
            "Blocked Valid Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "181818181800",
        )
        allowed_valid = make_workflow_person(
            "Allowed Valid Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "181818181801",
        )
        grant_change(allowed_valid, "person-valid")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_verify_valid", kwargs={"pk": blocked_valid.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_verify_valid", kwargs={"pk": allowed_valid.pk})
        )
        blocked_valid.refresh_from_db()
        allowed_valid.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_valid.verify_status, self.AccessRequestPerson.VERIFY_PENDING)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_valid.verify_status, self.AccessRequestPerson.VERIFY_VALID)

        blocked_invalid = make_workflow_person(
            "Blocked Invalid Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "181818181802",
        )
        allowed_invalid = make_workflow_person(
            "Allowed Invalid Scope",
            self.AccessRequest.STATUS_CONFIRMED,
            "181818181803",
        )
        grant_change(allowed_invalid, "person-invalid")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_verify_invalid", kwargs={"pk": blocked_invalid.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_verify_invalid", kwargs={"pk": allowed_invalid.pk})
        )
        blocked_invalid.refresh_from_db()
        allowed_invalid.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_invalid.verify_status, self.AccessRequestPerson.VERIFY_PENDING)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_invalid.verify_status, self.AccessRequestPerson.VERIFY_INVALID)

        blocked_in = make_workflow_person(
            "Blocked In Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "181818181804",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        allowed_in = make_workflow_person(
            "Allowed In Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "181818181805",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        grant_change(allowed_in, "person-in")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_in", kwargs={"pk": blocked_in.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_in", kwargs={"pk": allowed_in.pk})
        )
        blocked_in.refresh_from_db()
        allowed_in.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_in.access_status, self.AccessRequestPerson.ACCESS_OUT)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_in.access_status, self.AccessRequestPerson.ACCESS_IN)

        blocked_out = make_workflow_person(
            "Blocked Out Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "181818181806",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
            access_status=self.AccessRequestPerson.ACCESS_IN,
        )
        allowed_out = make_workflow_person(
            "Allowed Out Scope",
            self.AccessRequest.STATUS_ACCEPTED,
            "181818181807",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
            access_status=self.AccessRequestPerson.ACCESS_IN,
        )
        grant_change(allowed_out, "person-out")

        blocked_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_out", kwargs={"pk": blocked_out.pk})
        )
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequestperson_check_out", kwargs={"pk": allowed_out.pk})
        )
        blocked_out.refresh_from_db()
        allowed_out.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_out.access_status, self.AccessRequestPerson.ACCESS_IN)
        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(allowed_out.access_status, self.AccessRequestPerson.ACCESS_OUT)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_ui_reject_from_submitted_is_blocked_until_confirmed(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        access_request = self.make_request(name="Reject Requires Confirm")
        self.make_person(access_request)
        access_request.submit(user=self.user)
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change"])

        rejected_too_early = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_reject", kwargs={"pk": access_request.pk}),
            {"description": "Reject after review"},
        )
        access_request.refresh_from_db()

        self.assertEqual(rejected_too_early.status_code, 302)
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_SUBMITTED)

        access_request.confirm(user=self.user)
        allowed_response = self.client.post(
            reverse("plugins:netbox_smartlock:accessrequest_reject", kwargs={"pk": access_request.pk}),
            {"description": "Reject after review"},
        )
        access_request.refresh_from_db()

        self.assertEqual(allowed_response.status_code, 302)
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_REJECTED)

    def test_api_admin_workflow_uses_netbox_change_permission_not_add_permission(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        access_request = self.make_request(name="API Change Permission Flow")
        self.make_person(access_request)
        access_request.submit(user=self.user)
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view"])

        confirm_url = reverse(
            "plugins-api:netbox_smartlock-api:accessrequest-confirm",
            kwargs={"pk": access_request.pk},
        )
        blocked_response = self.client.post(confirm_url, data={}, content_type="application/json")
        access_request.refresh_from_db()

        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_SUBMITTED)

        self.grant_object_permission(self.AccessRequest, ["change"])
        allowed_response = self.client.post(confirm_url, data={}, content_type="application/json")
        access_request.refresh_from_db()

        self.assertEqual(allowed_response.status_code, 200, allowed_response.content.decode())
        self.assertEqual(access_request.status, self.AccessRequest.STATUS_CONFIRMED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_api_reject_requires_confirmed_status(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)
        submitted_request = self.make_request(name="API Reject Submitted")
        self.make_person(submitted_request)
        submitted_request.submit(user=self.user)
        confirmed_request = self.make_request(name="API Reject Confirmed", status=self.AccessRequest.STATUS_CONFIRMED)
        self.make_person(
            confirmed_request,
            identity_code="191919191900",
            full_name="API Reject Confirmed Person",
        )
        self.login()
        self.grant_object_permission(self.AccessRequest, ["view", "change"])

        submitted_response = self.client.post(
            reverse(
                "plugins-api:netbox_smartlock-api:accessrequest-reject",
                kwargs={"pk": submitted_request.pk},
            ),
            data={"description": "Reject reason"},
            content_type="application/json",
        )
        submitted_request.refresh_from_db()

        self.assertEqual(submitted_response.status_code, 400)
        self.assertEqual(submitted_request.status, self.AccessRequest.STATUS_SUBMITTED)

        confirmed_response = self.client.post(
            reverse(
                "plugins-api:netbox_smartlock-api:accessrequest-reject",
                kwargs={"pk": confirmed_request.pk},
            ),
            data={"description": "Reject reason"},
            content_type="application/json",
        )
        confirmed_request.refresh_from_db()

        self.assertEqual(confirmed_response.status_code, 200, confirmed_response.content.decode())
        self.assertEqual(confirmed_request.status, self.AccessRequest.STATUS_REJECTED)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_creator_notification_prefers_created_by_when_changelog_is_missing(self):
        creator = get_user_model().objects.create_user(
            username="creator-mail",
            password="test-password",
            email="creator@example.com",
        )
        access_request = self.make_request(
            name="Creator Email",
            status=self.AccessRequest.STATUS_CONFIRMED,
        )
        access_request.created_by = creator
        access_request.save(update_fields=("created_by", "last_updated"))
        self.make_person(
            access_request,
            identity_code="999900002222",
            full_name="Verified Email Person",
            verify_status=self.AccessRequestPerson.VERIFY_VALID,
        )
        ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(self.AccessRequest),
            changed_object_id=access_request.pk,
            action=ObjectChangeActionChoices.ACTION_CREATE,
        ).delete()

        access_request.accept(user=self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["creator@example.com"])
