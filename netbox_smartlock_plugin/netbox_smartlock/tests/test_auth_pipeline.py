from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from core.models import ObjectType
from dcim.models import Device, Location, Rack, Region, Site
from users.models import Group, ObjectPermission

from netbox_smartlock.api.authentication import KeycloakOIDCAuthentication
from netbox_smartlock.auth_pipeline import sync_keycloak_groups
from netbox_smartlock.models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock


class KeycloakGroupSyncPipelineTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="oidc-user")

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
    )
    def test_sync_adds_allow_listed_keycloak_groups(self):
        result = sync_keycloak_groups(None, self.user, {"groups": ["Admin", "Unmanaged"]})

        self.assertEqual(result, {"user": self.user})
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Admin"])
        self.assertFalse(Group.objects.filter(name="Unmanaged").exists())

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
    )
    def test_sync_removes_stale_managed_groups(self):
        admin_group = Group.objects.create(name="Admin")
        unmanaged_group = Group.objects.create(name="LocalOnly")
        self.user.groups.add(admin_group, unmanaged_group)

        sync_keycloak_groups(None, self.user, {"groups": ["Guest"]})

        self.assertEqual(set(self.user.groups.values_list("name", flat=True)), {"Guest", "LocalOnly"})

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
    )
    def test_missing_groups_claim_leaves_existing_groups_intact(self):
        admin_group = Group.objects.create(name="Admin")
        self.user.groups.add(admin_group)

        sync_keycloak_groups(None, self.user, {"email": "oidc-user@example.com"})

        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Admin"])

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
    )
    def test_full_path_group_names_are_normalized(self):
        sync_keycloak_groups(None, self.user, {"groups": ["/Admin"]})

        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Admin"])

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
        KEYCLOAK_GROUP_SYNC_GROUP_MAP={"dcim-admin": "Admin", "dcim-guest": "Guest"},
    )
    def test_keycloak_groups_are_mapped_to_netbox_groups(self):
        sync_keycloak_groups(None, self.user, {"groups": ["dcim-admin"]})

        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Admin"])

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
        KEYCLOAK_GROUP_SYNC_ROLE_MAP={"dcim-admin": "Admin", "dcim-guest": "Guest"},
    )
    def test_realm_roles_are_mapped_to_netbox_groups(self):
        sync_keycloak_groups(None, self.user, {"realm_access": {"roles": ["dcim-admin"]}})

        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Admin"])

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
        KEYCLOAK_GROUP_SYNC_ROLE_MAP="dcim-admin=Admin dcim-guest=Guest",
    )
    def test_resource_roles_are_mapped_from_env_style_config(self):
        sync_keycloak_groups(
            None,
            self.user,
            {
                "resource_access": {
                    "netbox-dev": {
                        "roles": ["dcim-guest"],
                    }
                }
            },
        )

        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), ["Guest"])


class SmartLockRbacBootstrapTest(TestCase):
    def test_bootstrap_creates_admin_and_guest_permissions(self):
        call_command("smartlock_bootstrap_rbac")

        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Admin - AccessRequest workflow").exists())
        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Admin - Asset catalogs").exists())
        self.assertTrue(ObjectPermission.objects.filter(name="SmartLock Guest - AccessRequest own records").exists())

        admin_group = Group.objects.get(name="Admin")
        guest_group = Group.objects.get(name="Guest")
        admin_permission = ObjectPermission.objects.get(name="SmartLock Admin - AccessRequest workflow")
        admin_catalog_permission = ObjectPermission.objects.get(name="SmartLock Admin - Asset catalogs")
        admin_scope_permission = ObjectPermission.objects.get(name="SmartLock Admin - DCIM scope view")
        guest_permission = ObjectPermission.objects.get(name="SmartLock Guest - AccessRequest own records")

        self.assertIn(admin_group, admin_permission.groups.all())
        self.assertIn(admin_group, admin_catalog_permission.groups.all())
        self.assertIn(guest_group, guest_permission.groups.all())
        self.assertEqual(admin_permission.actions, ["view", "change"])
        self.assertEqual(admin_catalog_permission.actions, ["view", "add", "change", "delete"])
        self.assertEqual(guest_permission.constraints, {"created_by_id": "$user.id"})
        self.assertPermissionModels(admin_permission, {AccessRequest})
        self.assertPermissionModels(admin_catalog_permission, {AssetGroup, Asset, SmartLock})
        self.assertPermissionModels(admin_scope_permission, {Region, Site, Location, Rack, Device})

    def assertPermissionModels(self, permission, models):
        expected = {
            (object_type.app_label, object_type.model)
            for object_type in (ObjectType.objects.get_for_model(model) for model in models)
        }
        actual = set(permission.object_types.values_list("app_label", "model"))
        self.assertEqual(actual, expected)

    def test_bootstrap_repairs_managed_permission_group_links(self):
        call_command("smartlock_bootstrap_rbac")
        permission = ObjectPermission.objects.get(name="SmartLock Admin - Asset catalogs")
        permission.groups.clear()

        call_command("smartlock_bootstrap_rbac")

        self.assertEqual(list(permission.groups.values_list("name", flat=True)), ["Admin"])


class KeycloakOIDCApiAuthenticationTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @override_settings(
        KEYCLOAK_GROUP_SYNC_ENABLED=True,
        KEYCLOAK_GROUP_SYNC_GROUPS=("Admin", "Guest"),
        KEYCLOAK_GROUP_SYNC_REMOVE=True,
        KEYCLOAK_GROUP_SYNC_GROUP_MAP={"dcim-admin": "Admin", "dcim-guest": "Guest"},
        KEYCLOAK_GROUP_SYNC_ROLE_MAP={"dcim-admin": "Admin", "dcim-guest": "Guest"},
    )
    def test_authenticates_keycloak_jwt_payload_and_syncs_groups(self):
        payload = {
            "sub": "subject-1",
            "preferred_username": "ldap-admin",
            "email": "ldap-admin@example.org",
            "given_name": "LDAP",
            "family_name": "Admin",
            "groups": ["dcim-admin"],
            "realm_access": {"roles": ["dcim-admin"]},
        }
        seen = {}

        class TestAuthentication(KeycloakOIDCAuthentication):
            def decode_token(self, token):
                seen["token"] = token
                return payload

        request = self.factory.get(
            "/api/plugins/smartlock/asset-groups/",
            HTTP_AUTHORIZATION="Bearer header.payload.signature",
        )

        user, auth_payload = TestAuthentication().authenticate(request)

        self.assertEqual(seen["token"], "header.payload.signature")
        self.assertEqual(auth_payload, payload)
        self.assertEqual(user.username, "ldap-admin")
        self.assertEqual(user.email, "ldap-admin@example.org")
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Admin"])

    def test_ignores_non_jwt_bearer_values_for_netbox_token_auth(self):
        request = self.factory.get(
            "/api/plugins/smartlock/asset-groups/",
            HTTP_AUTHORIZATION="Bearer nbt_abc.def",
        )

        self.assertIsNone(KeycloakOIDCAuthentication().authenticate(request))
