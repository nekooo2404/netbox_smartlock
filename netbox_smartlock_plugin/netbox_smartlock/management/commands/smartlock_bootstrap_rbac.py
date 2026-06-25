from os import environ

from django.core.management.base import BaseCommand

from core.models import ObjectType
from dcim.models import Device, Location, Rack, Region, Site
from users.models import Group, ObjectPermission

from netbox_smartlock.models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock
from netbox_smartlock.auth_pipeline import _config_value


def setting_as_bool(name, default=False):
    value = _config_value(name, environ.get(name, default))
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def ensure_permission(name, group, models, actions, constraints=None, description=""):
    permission, _ = ObjectPermission.objects.update_or_create(
        name=name,
        defaults={
            "description": description,
            "actions": actions,
            "constraints": constraints,
            "enabled": True,
        },
    )
    permission.groups.set((group,))
    permission.object_types.set(ObjectType.objects.get_for_model(model) for model in models)
    return permission


def remove_permission(name):
    ObjectPermission.objects.filter(name=name).delete()


class Command(BaseCommand):
    help = "Bootstrap NetBox RBAC used by the SmartLock Keycloak Admin/Guest groups."

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        guest_group, _ = Group.objects.get_or_create(name="Guest")
        keycloak_scope_sync_enabled = setting_as_bool("KEYCLOAK_SCOPE_SYNC_ENABLED", False)

        if not keycloak_scope_sync_enabled:
            ensure_permission(
                name="SmartLock Admin - AccessRequest workflow",
                group=admin_group,
                models=(AccessRequest,),
                actions=["view", "change"],
                description="Allow DCIM admins to view and run workflow actions for access requests.",
            )
            ensure_permission(
                name="SmartLock Admin - AccessRequestPerson workflow",
                group=admin_group,
                models=(AccessRequestPerson,),
                actions=["view", "change"],
                description="Allow DCIM admins to verify identities and record in/out workflow events.",
            )
        else:
            remove_permission("SmartLock Admin - AccessRequest workflow")
            remove_permission("SmartLock Admin - AccessRequestPerson workflow")
        if keycloak_scope_sync_enabled:
            ensure_permission(
                name="SmartLock Admin - Asset groups",
                group=admin_group,
                models=(AssetGroup,),
                actions=["view", "add", "change", "delete"],
                description="Allow DCIM admins to manage SmartLock asset groups.",
            )
            remove_permission("SmartLock Admin - Asset catalogs")
            remove_permission("SmartLock Admin - DCIM scope view")
        else:
            ensure_permission(
                name="SmartLock Admin - Asset catalogs",
                group=admin_group,
                models=(AssetGroup, Asset, SmartLock),
                actions=["view", "add", "change", "delete"],
                description=(
                    "Allow DCIM admins to manage asset groups, device assets, and Smart Locks "
                    "through the NetBox UI/API."
                ),
            )
            ensure_permission(
                name="SmartLock Admin - DCIM scope view",
                group=admin_group,
                models=(Region, Site, Location, Rack, Device),
                actions=["view"],
                description="Allow DCIM admins to select DCIM scope objects in SmartLock workflows and asset catalogs.",
            )

        ensure_permission(
            name="SmartLock Guest - AccessRequest own records",
            group=guest_group,
            models=(AccessRequest,),
            actions=["view", "add", "change", "delete"],
            constraints={"created_by": "$user"},
            description="Allow guests to manage only access requests created by themselves.",
        )
        ensure_permission(
            name="SmartLock Guest - AccessRequestPerson own request records",
            group=guest_group,
            models=(AccessRequestPerson,),
            actions=["view", "add", "change", "delete"],
            constraints={"request__created_by": "$user"},
            description="Allow guests to manage identities only on access requests created by themselves.",
        )
        if not keycloak_scope_sync_enabled:
            ensure_permission(
                name="SmartLock Guest - DCIM scope view",
                group=guest_group,
                models=(Region, Site, Location),
                actions=["view"],
                description=(
                    "Allow guests to select Region/Site/Location objects. "
                    "Add constraints manually for customer-specific scope."
                ),
            )
        else:
            remove_permission("SmartLock Guest - DCIM scope view")

        self.stdout.write(self.style.SUCCESS("SmartLock RBAC bootstrap complete."))
