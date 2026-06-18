import logging
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


def sync_keycloak_groups(backend, user, response, *args, **kwargs):
    """
    Sync allow-listed Keycloak OIDC groups/roles into NetBox groups on every login.

    Only NetBox groups configured in KEYCLOAK_GROUP_SYNC_GROUPS are managed.
    Keycloak groups can be mapped to NetBox group names with KEYCLOAK_GROUP_SYNC_GROUP_MAP.
    Keycloak roles can be mapped to NetBox group names with KEYCLOAK_GROUP_SYNC_ROLE_MAP.
    Missing claims are treated as a mapper/config issue and leave existing groups intact.
    Explicit empty group/role claims remove managed groups when removal is enabled.
    """
    if not _setting_as_bool("KEYCLOAK_GROUP_SYNC_ENABLED", False):
        return {"user": user}
    if not user:
        return {"user": user}

    managed_groups = _setting_as_set("KEYCLOAK_GROUP_SYNC_GROUPS", ())
    if not managed_groups:
        logger.warning("KEYCLOAK_GROUP_SYNC_ENABLED is true but no managed groups are configured")
        return {"user": user}

    group_map = _setting_as_mapping("KEYCLOAK_GROUP_SYNC_GROUP_MAP", ())
    role_map = _setting_as_mapping("KEYCLOAK_GROUP_SYNC_ROLE_MAP", ())
    keycloak_groups = _netbox_group_names_from_response(response, group_map, role_map)
    if keycloak_groups is None:
        logger.warning("OIDC response for user %s has no groups/roles claim; skipping NetBox group sync", user)
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

    return {"user": user}
