from django.core.management.base import BaseCommand

from core.models import ObjectType
from dcim.models import Device, Location, Rack, Region, Site
from users.models import Group, ObjectPermission

from netbox_smartlock.models import AccessRequest, AccessRequestPerson, Asset, AssetGroup, SmartLock


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


class Command(BaseCommand):
    help = "Bootstrap NetBox RBAC used by the SmartLock Admin/Guest groups."

    def handle(self, *args, **options):
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        guest_group, _ = Group.objects.get_or_create(name="Guest")
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

        self.stdout.write(self.style.SUCCESS("SmartLock RBAC bootstrap complete."))
