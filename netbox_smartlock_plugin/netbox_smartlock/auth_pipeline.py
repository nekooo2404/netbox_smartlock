import logging
from hashlib import sha1
import json
from os import environ

from django.conf import settings


logger = logging.getLogger("netbox_smartlock.auth_pipeline")


def _config_value(name, default=None):
    if hasattr(settings, name):
        return getattr(settings, name)
    try:
        import netbox.configuration as netbox_config

        if hasattr(netbox_config, name):
            return getattr(netbox_config, name)
    except Exception:
        pass
    return environ.get(name, default)


def _setting_as_bool(name, default=False):
    value = _config_value(name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _setting_as_set(name, default=()):
    value = _config_value(name, default)
    if value is None:
        return set()
    if isinstance(value, str):
        items = value.replace(",", " ").split()
    else:
        items = value
    return {str(item).strip() for item in items if str(item).strip()}


def _setting_as_mapping(name, default=()):
    value = _config_value(name, default)
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(key).strip(): str(val).strip() for key, val in value.items() if str(key).strip() and str(val).strip()}

    if isinstance(value, str):
        items = value.replace(",", " ").split()
    else:
        items = value

    mapping = {}
    for item in items:
        pair = str(item).strip()
        if not pair:
            continue
        separator = "=" if "=" in pair else ":"
        if separator not in pair:
            continue
        source, target = pair.split(separator, 1)
        source = source.strip()
        target = target.strip()
        if source and target:
            mapping[source] = target
    return mapping


def _normalize_group_name(value):
    name = str(value).strip()
    if not name:
        return ""
    name = name.strip("/")
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name.strip()


def _groups_from_response(response):
    if not isinstance(response, dict) or "groups" not in response:
        return None

    raw_groups = response.get("groups") or []
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]

    groups = set()
    for raw_group in raw_groups:
        group_name = _normalize_group_name(raw_group)
        if group_name:
            groups.add(group_name)
    return groups


def _values_from_claim(value):
    if value is None:
        return set()
    if isinstance(value, str):
        values = [value]
    else:
        values = value
    return {str(item).strip() for item in values if str(item).strip()}


def _claim_value_from_response(response, claim_name):
    if not isinstance(response, dict) or not claim_name:
        return False, None

    current = response
    for part in str(claim_name).split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current.get(part)
    return True, current


def _scope_values_from_claim(value):
    if value is None:
        return set()
    if isinstance(value, str):
        values = value.replace(",", " ").split()
    else:
        values = value
    return {str(item).strip().strip("/") for item in values if str(item).strip().strip("/")}


def _roles_from_response(response):
    if not isinstance(response, dict):
        return None

    claim_seen = False
    roles = set()

    if "roles" in response:
        claim_seen = True
        roles |= _values_from_claim(response.get("roles"))

    realm_access = response.get("realm_access")
    if isinstance(realm_access, dict) and "roles" in realm_access:
        claim_seen = True
        roles |= _values_from_claim(realm_access.get("roles"))

    resource_access = response.get("resource_access")
    if isinstance(resource_access, dict):
        for access in resource_access.values():
            if isinstance(access, dict) and "roles" in access:
                claim_seen = True
                roles |= _values_from_claim(access.get("roles"))

    if not claim_seen:
        return None
    return roles


def _netbox_group_names_from_response(response, group_map, role_map):
    keycloak_groups = _groups_from_response(response)
    keycloak_roles = _roles_from_response(response)

    if keycloak_groups is None and keycloak_roles is None:
        return None

    group_names = set()
    for group in keycloak_groups or ():
        mapped_group = group_map.get(group, group)
        group_name = _normalize_group_name(mapped_group)
        if group_name:
            group_names.add(group_name)

    for role in keycloak_roles or ():
        mapped_group = role_map.get(role, role)
        group_name = _normalize_group_name(mapped_group)
        if group_name:
            group_names.add(group_name)
    return group_names


def _scope_claims_from_response(response):
    region_claim = str(_config_value("KEYCLOAK_SCOPE_SYNC_REGION_CLAIM", "dcim_regions") or "").strip()
    site_claim = str(_config_value("KEYCLOAK_SCOPE_SYNC_SITE_CLAIM", "dcim_sites") or "").strip()

    region_seen, region_value = _claim_value_from_response(response, region_claim)
    site_seen, site_value = _claim_value_from_response(response, site_claim)
    if not region_seen and not site_seen:
        return None

    return {
        "regions": _scope_values_from_claim(region_value),
        "sites": _scope_values_from_claim(site_value),
    }


def _permission_digest(model, actions, constraints):
    payload = json.dumps(
        {
            "model": model._meta.label_lower,
            "actions": list(actions),
            "constraints": constraints,
        },
        sort_keys=True,
    )
    return sha1(payload.encode("utf-8")).hexdigest()[:12]


def _managed_scope_prefix(user):
    prefix = str(_config_value("KEYCLOAK_SCOPE_SYNC_PERMISSION_PREFIX", "SmartLock Keycloak Scope") or "").strip()
    if not prefix:
        prefix = "SmartLock Keycloak Scope"
    return f"{prefix} u{user.pk} "


def _scope_permission_specs(user, region_scope_slugs, site_scope_slugs):
    from dcim.models import Device, Location, Rack, Region, Site
    from netbox_smartlock.models import AccessRequest, AccessRequestPerson, Asset, SmartLock

    specs = []

    def add(model, actions, constraints, description):
        specs.append(
            {
                "model": model,
                "actions": tuple(actions),
                "constraints": constraints,
                "description": description,
            }
        )

    region_scope_slugs = set(region_scope_slugs)
    site_scope_slugs = set(site_scope_slugs)

    parent_region_slugs = set(
        Site.objects.filter(slug__in=site_scope_slugs, region__isnull=False).values_list("region__slug", flat=True)
    )
    display_region_slugs = region_scope_slugs | parent_region_slugs

    for slug in sorted(display_region_slugs):
        add(Region, ("view",), {"slug": slug}, f"Allow Keycloak-scoped Region {slug}.")

    for slug in sorted(region_scope_slugs):
        add(Site, ("view",), {"region__slug": slug}, f"Allow Sites in Keycloak-scoped Region {slug}.")
        add(Location, ("view",), {"site__region__slug": slug}, f"Allow Locations in Keycloak-scoped Region {slug}.")
        add(Rack, ("view",), {"site__region__slug": slug}, f"Allow Racks in Keycloak-scoped Region {slug}.")
        add(Device, ("view",), {"site__region__slug": slug}, f"Allow Devices in Keycloak-scoped Region {slug}.")

    for slug in sorted(site_scope_slugs):
        add(Site, ("view",), {"slug": slug}, f"Allow Keycloak-scoped Site {slug}.")
        add(Location, ("view",), {"site__slug": slug}, f"Allow Locations in Keycloak-scoped Site {slug}.")
        add(Rack, ("view",), {"site__slug": slug}, f"Allow Racks in Keycloak-scoped Site {slug}.")
        add(Device, ("view",), {"site__slug": slug}, f"Allow Devices in Keycloak-scoped Site {slug}.")

    is_admin = bool(user.groups.filter(name="Admin").exists() or user.is_superuser)
    if not is_admin:
        return specs

    admin_actions = ("view", "add", "change", "delete")
    workflow_actions = ("view", "change")
    for slug in sorted(region_scope_slugs):
        add(Asset, admin_actions, {"region__slug": slug}, f"Allow SmartLock assets in Keycloak Region {slug}.")
        add(SmartLock, admin_actions, {"region__slug": slug}, f"Allow Smart Locks in Keycloak Region {slug}.")
        add(AccessRequest, workflow_actions, {"region__slug": slug}, f"Allow access requests in Keycloak Region {slug}.")
        add(
            AccessRequestPerson,
            workflow_actions,
            {"request__region__slug": slug},
            f"Allow access request persons in Keycloak Region {slug}.",
        )

    for slug in sorted(site_scope_slugs):
        add(Asset, admin_actions, {"site__slug": slug}, f"Allow SmartLock assets in Keycloak Site {slug}.")
        add(SmartLock, admin_actions, {"site__slug": slug}, f"Allow Smart Locks in Keycloak Site {slug}.")
        add(AccessRequest, workflow_actions, {"site__slug": slug}, f"Allow access requests in Keycloak Site {slug}.")
        add(
            AccessRequestPerson,
            workflow_actions,
            {"request__site__slug": slug},
            f"Allow access request persons in Keycloak Site {slug}.",
        )

    return specs


def sync_keycloak_scope(user, response):
    """
    Sync Keycloak Region/Site claims into user-specific NetBox ObjectPermissions.

    Keycloak remains the authorization source for regional scope, while NetBox
    keeps enforcing scope through its native ObjectPermission backend.
    """
    if not _setting_as_bool("KEYCLOAK_SCOPE_SYNC_ENABLED", False):
        return
    if not user or not user.pk:
        return

    scope_claims = _scope_claims_from_response(response)
    if scope_claims is None:
        logger.warning("OIDC response for user %s has no Region/Site scope claims; skipping scope sync", user)
        return

    from core.models import ObjectType
    from users.models import ObjectPermission

    specs = _scope_permission_specs(user, scope_claims["regions"], scope_claims["sites"])
    prefix = _managed_scope_prefix(user)
    desired_names = set()

    for spec in specs:
        name = f"{prefix}{_permission_digest(spec['model'], spec['actions'], spec['constraints'])}"
        desired_names.add(name)
        permission, _ = ObjectPermission.objects.update_or_create(
            name=name,
            defaults={
                "description": spec["description"],
                "actions": list(spec["actions"]),
                "constraints": spec["constraints"],
                "enabled": True,
            },
        )
        permission.users.set((user,))
        permission.groups.clear()
        permission.object_types.set((ObjectType.objects.get_for_model(spec["model"]),))

    if _setting_as_bool("KEYCLOAK_SCOPE_SYNC_REMOVE", True):
        stale_permissions = ObjectPermission.objects.filter(name__startswith=prefix).exclude(name__in=desired_names)
        stale_permissions.delete()


def sync_keycloak_groups(backend, user, response, *args, **kwargs):
    """
    Sync allow-listed Keycloak OIDC groups/roles into NetBox groups on every login.

    Only NetBox groups configured in KEYCLOAK_GROUP_SYNC_GROUPS are managed.
    Keycloak groups can be mapped to NetBox group names with KEYCLOAK_GROUP_SYNC_GROUP_MAP.
    Keycloak roles can be mapped to NetBox group names with KEYCLOAK_GROUP_SYNC_ROLE_MAP.
    Missing claims are treated as a mapper/config issue and leave existing groups intact.
    Explicit empty group/role claims remove managed groups when removal is enabled.
    """
    if not user:
        return {"user": user}

    backend_name = getattr(backend, "name", None)
    if backend_name and backend_name != "oidc":
        return {"user": user}

    if not _setting_as_bool("KEYCLOAK_GROUP_SYNC_ENABLED", False):
        sync_keycloak_scope(user, response)
        return {"user": user}

    managed_groups = _setting_as_set("KEYCLOAK_GROUP_SYNC_GROUPS", ())
    if not managed_groups:
        logger.warning("KEYCLOAK_GROUP_SYNC_ENABLED is true but no managed groups are configured")
        sync_keycloak_scope(user, response)
        return {"user": user}

    group_map = _setting_as_mapping("KEYCLOAK_GROUP_SYNC_GROUP_MAP", ())
    role_map = _setting_as_mapping("KEYCLOAK_GROUP_SYNC_ROLE_MAP", ())
    keycloak_groups = _netbox_group_names_from_response(response, group_map, role_map)
    if keycloak_groups is None:
        logger.warning("OIDC response for user %s has no groups/roles claim; skipping NetBox group sync", user)
        sync_keycloak_scope(user, response)
        return {"user": user}

    target_group_names = keycloak_groups & managed_groups
    from users.models import Group

    target_groups = [Group.objects.get_or_create(name=name)[0] for name in sorted(target_group_names)]

    if target_groups:
        user.groups.add(*target_groups)

    if _setting_as_bool("KEYCLOAK_GROUP_SYNC_REMOVE", True):
        remove_group_names = managed_groups - target_group_names
        if remove_group_names:
            user.groups.remove(*Group.objects.filter(name__in=remove_group_names))

    sync_keycloak_scope(user, response)

    return {"user": user}
