from django.core.management import call_command
from django.test import TestCase

from core.models import ObjectType
from dcim.models import Device, Location, Rack, Region, Site
from users.models import Group, ObjectPermission

from netbox_smartlock.models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock


class SmartLockRbacBootstrapTest(TestCase):
    def test_bootstrap_creates_admin_and_guest_permissions(self):
        call_command("smartlock_bootstrap_rbac")

        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Admin - AccessRequest workflow").exists())
        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Admin - Asset catalogs").exists())
        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Guest - AccessRequest own records").exists())

        admin_group = Group.objects.get(name="Admin")
        guest_group = Group.objects.get(name="Guest")
        admin_workflow_permission = ObjectPermission.objects.get(name="SmartLock Admin - AccessRequest workflow")
        admin_person_permission = ObjectPermission.objects.get(name="SmartLock Admin - AccessRequestPerson workflow")
        admin_catalog_permission = ObjectPermission.objects.get(name="SmartLock Admin - Asset catalogs")
        admin_scope_permission = ObjectPermission.objects.get(name="SmartLock Admin - DCIM scope view")
        guest_request_permission = ObjectPermission.objects.get(name="SmartLock Guest - AccessRequest own records")
        guest_person_permission = ObjectPermission.objects.get(
            name="SmartLock Guest - AccessRequestPerson own request records"
        )
        guest_scope_permission = ObjectPermission.objects.get(name="SmartLock Guest - DCIM scope view")

        self.assertIn(admin_group, admin_workflow_permission.groups.all())
        self.assertIn(admin_group, admin_person_permission.groups.all())
        self.assertIn(admin_group, admin_catalog_permission.groups.all())
        self.assertIn(admin_group, admin_scope_permission.groups.all())
        self.assertIn(guest_group, guest_request_permission.groups.all())
        self.assertIn(guest_group, guest_person_permission.groups.all())
        self.assertIn(guest_group, guest_scope_permission.groups.all())

        self.assertEqual(admin_workflow_permission.actions, ["view", "change"])
        self.assertEqual(admin_person_permission.actions, ["view", "change"])
        self.assertEqual(admin_catalog_permission.actions, ["view", "add", "change", "delete"])
        self.assertEqual(admin_scope_permission.actions, ["view"])
        self.assertEqual(guest_request_permission.constraints, {"created_by": "$user"})
        self.assertEqual(guest_person_permission.constraints, {"request__created_by": "$user"})

        self.assertPermissionModels(admin_workflow_permission, {AccessRequest})
        self.assertPermissionModels(admin_person_permission, {AccessRequestPerson})
        self.assertPermissionModels(admin_catalog_permission, {AssetGroup, Asset, SmartLock})
        self.assertPermissionModels(admin_scope_permission, {Region, Site, Location, Rack, Device})
        self.assertPermissionModels(guest_scope_permission, {Region, Site, Location})

    def test_bootstrap_repairs_managed_permission_group_links(self):
        call_command("smartlock_bootstrap_rbac")
        permission = ObjectPermission.objects.get(name="SmartLock Admin - Asset catalogs")
        permission.groups.clear()

        call_command("smartlock_bootstrap_rbac")

        self.assertEqual(list(permission.groups.values_list("name", flat=True)), ["Admin"])

    def assertPermissionModels(self, permission, models):
        expected = {
            (object_type.app_label, object_type.model)
            for object_type in (ObjectType.objects.get_for_model(model) for model in models)
        }
        actual = set(permission.object_types.values_list("app_label", "model"))
        self.assertEqual(actual, expected)
