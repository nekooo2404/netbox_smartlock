#!/usr/bin/env python3
import json
import sys
from urllib.parse import quote

import requests


BASE_URL = "http://localhost:8080"
MASTER_REALM = "master"
REALM = "netbox-dev"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin"
CLIENT_ID = "netbox-dev"


class KeycloakError(RuntimeError):
    pass


def request(method, path, token=None, expected=(200, 201, 204), **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
    if response.status_code not in expected:
        raise KeycloakError(
            f"{method} {path} failed with {response.status_code}: {response.text[:1000]}"
        )
    if response.status_code == 204 or not response.text.strip():
        return None
    return response.json()


def get_admin_token():
    response = requests.post(
        f"{BASE_URL}/realms/{MASTER_REALM}/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise KeycloakError(f"admin login failed with {response.status_code}: {response.text[:1000]}")
    return response.json()["access_token"]


def get_realm(token):
    return request("GET", f"/admin/realms/{REALM}", token=token)


def get_role(token, name):
    path_name = quote(name, safe="")
    response = requests.get(
        f"{BASE_URL}/admin/realms/{REALM}/roles/{path_name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise KeycloakError(f"GET role {name} failed with {response.status_code}: {response.text[:1000]}")
    return response.json()


def ensure_role(token, name, description):
    role = get_role(token, name)
    if role:
        return role
    request(
        "POST",
        f"/admin/realms/{REALM}/roles",
        token=token,
        expected=(201, 204),
        json={"name": name, "description": description},
    )
    return get_role(token, name)


def all_groups(token):
    return request("GET", f"/admin/realms/{REALM}/groups?briefRepresentation=false", token=token)


def flatten_groups(groups):
    result = []
    for group in groups:
        result.append(group)
        result.extend(flatten_groups(group.get("subGroups") or []))
    return result


def get_group(token, name):
    matches = [group for group in flatten_groups(all_groups(token)) if group.get("path") == f"/{name}"]
    return matches[0] if matches else None


def ensure_group(token, name):
    group = get_group(token, name)
    if group:
        return group
    request(
        "POST",
        f"/admin/realms/{REALM}/groups",
        token=token,
        expected=(201, 204),
        json={"name": name},
    )
    return get_group(token, name)


def ensure_group_role(token, group_name, role_name):
    group = ensure_group(token, group_name)
    role = ensure_role(token, role_name, f"{role_name} role")
    assigned = request(
        "GET",
        f"/admin/realms/{REALM}/groups/{group['id']}/role-mappings/realm",
        token=token,
    )
    if any(item.get("name") == role_name for item in assigned):
        return
    request(
        "POST",
        f"/admin/realms/{REALM}/groups/{group['id']}/role-mappings/realm",
        token=token,
        expected=(204,),
        json=[role],
    )


def get_client(token, client_id):
    clients = request(
        "GET",
        f"/admin/realms/{REALM}/clients?clientId={quote(client_id, safe='')}",
        token=token,
    )
    if not clients:
        raise KeycloakError(f"client {client_id!r} was not found")
    return clients[0]


def find_users(token, username):
    return request(
        "GET",
        f"/admin/realms/{REALM}/users?username={quote(username, safe='')}&exact=true",
        token=token,
    )


def delete_user(token, user_id):
    request(
        "DELETE",
        f"/admin/realms/{REALM}/users/{quote(user_id, safe='')}",
        token=token,
        expected=(204,),
    )


def ensure_legacy_app_users_absent(token):
    removed = []
    for username in ("netbox-admin",):
        for user in find_users(token, username):
            delete_user(token, user["id"])
            removed.append(username)
    return removed


def get_client_detail(token, client_uuid):
    return request("GET", f"/admin/realms/{REALM}/clients/{client_uuid}", token=token)


def ensure_client_mapper(token, client_uuid, mapper):
    client = get_client_detail(token, client_uuid)
    if any(item.get("name") == mapper["name"] for item in client.get("protocolMappers") or []):
        return
    request(
        "POST",
        f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        token=token,
        expected=(201, 204),
        json=mapper,
    )


def all_components(token):
    return request("GET", f"/admin/realms/{REALM}/components", token=token)


def find_component(token, provider_type, name, parent_id=None):
    for component in all_components(token):
        if component.get("providerType") != provider_type or component.get("name") != name:
            continue
        if parent_id and component.get("parentId") != parent_id:
            continue
        return component
    return None


def ensure_component(token, component):
    existing = find_component(
        token,
        component["providerType"],
        component["name"],
        component.get("parentId"),
    )
    if existing:
        return existing
    request(
        "POST",
        f"/admin/realms/{REALM}/components",
        token=token,
        expected=(201, 204),
        json=component,
    )
    created = find_component(
        token,
        component["providerType"],
        component["name"],
        component.get("parentId"),
    )
    if not created:
        raise KeycloakError(f"component {component['name']!r} was not created")
    return created


def ensure_ldap_provider(token):
    realm = get_realm(token)
    provider = ensure_component(
        token,
        {
            "name": "ldap-internal",
            "providerId": "ldap",
            "providerType": "org.keycloak.storage.UserStorageProvider",
            "parentId": realm["id"],
            "config": {
                "enabled": ["true"],
                "priority": ["0"],
                "fullSyncPeriod": ["-1"],
                "changedSyncPeriod": ["-1"],
                "cachePolicy": ["DEFAULT"],
                "editMode": ["READ_ONLY"],
                "importEnabled": ["true"],
                "syncRegistrations": ["false"],
                "vendor": ["other"],
                "connectionUrl": ["ldap://ldap:389"],
                "connectionPooling": ["true"],
                "authType": ["simple"],
                "bindDn": ["cn=admin,dc=example,dc=org"],
                "bindCredential": ["admin"],
                "usersDn": ["ou=users,dc=example,dc=org"],
                "usernameLDAPAttribute": ["uid"],
                "rdnLDAPAttribute": ["uid"],
                "uuidLDAPAttribute": ["entryUUID"],
                "userObjectClasses": ["inetOrgPerson, organizationalPerson"],
                "searchScope": ["1"],
                "pagination": ["false"],
                "batchSizeForSync": ["1000"],
                "validatePasswordPolicy": ["false"],
                "trustEmail": ["true"],
                "useTruststoreSpi": ["ldapsOnly"],
                "allowKerberosAuthentication": ["false"],
                "useKerberosForPasswordAuthentication": ["false"],
            },
        },
    )
    ensure_component(
        token,
        {
            "name": "groups",
            "providerId": "group-ldap-mapper",
            "providerType": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
            "parentId": provider["id"],
            "config": {
                "mode": ["READ_ONLY"],
                "groups.dn": ["ou=groups,dc=example,dc=org"],
                "group.name.ldap.attribute": ["cn"],
                "group.object.classes": ["groupOfNames"],
                "preserve.group.inheritance": ["true"],
                "membership.ldap.attribute": ["member"],
                "membership.attribute.type": ["DN"],
                "membership.user.ldap.attribute": ["uid"],
                "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
                "memberof.ldap.attribute": ["memberOf"],
                "groups.path": ["/"],
                "ignore.missing.groups": ["true"],
            },
        },
    )
    return provider


def sync_ldap(token, provider_id):
    response = requests.post(
        f"{BASE_URL}/admin/realms/{REALM}/user-storage/{provider_id}/sync",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        params={"action": "triggerFullSync"},
        timeout=60,
    )
    if response.status_code not in (200, 201, 204):
        raise KeycloakError(f"LDAP sync failed with {response.status_code}: {response.text[:1000]}")
    return response.text.strip()


def main():
    token = get_admin_token()

    removed_users = ensure_legacy_app_users_absent(token)

    ensure_role(token, "dcim-admin", "DCIM administrator mapped to NetBox Admin group")
    ensure_role(token, "dcim-guest", "DCIM guest mapped to NetBox Guest group")

    provider = ensure_ldap_provider(token)
    sync_result = sync_ldap(token, provider["id"])

    ensure_group_role(token, "Admin", "dcim-admin")
    ensure_group_role(token, "Guest", "dcim-guest")
    ensure_group_role(token, "dcim-admin", "dcim-admin")
    ensure_group_role(token, "dcim-guest", "dcim-guest")

    client = get_client(token, CLIENT_ID)
    ensure_client_mapper(
        token,
        client["id"],
        {
            "name": "groups",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-group-membership-mapper",
            "consentRequired": False,
            "config": {
                "full.path": "false",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
                "claim.name": "groups",
                "jsonType.label": "String",
                "multivalued": "true",
            },
        },
    )
    ensure_client_mapper(
        token,
        client["id"],
        {
            "name": "realm roles",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-realm-role-mapper",
            "consentRequired": False,
            "config": {
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
                "claim.name": "roles",
                "jsonType.label": "String",
                "multivalued": "true",
            },
        },
    )

    print(
        json.dumps(
            {
                "realm": REALM,
                "ldap_provider": provider["id"],
                "ldap_sync": sync_result,
                "client": CLIENT_ID,
                "roles": ["dcim-admin", "dcim-guest"],
                "groups": ["Admin", "Guest"],
                "removed_legacy_users": removed_users,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
