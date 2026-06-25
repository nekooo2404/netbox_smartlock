#!/usr/bin/env python3
import json
from os import environ
from pathlib import Path
import re
import sys
from urllib.parse import quote

import requests


def load_dotenv_if_missing(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) and name not in environ:
            environ[name] = value.strip().strip('"').strip("'")


load_dotenv_if_missing(Path(__file__).resolve().parents[1] / "env" / "netbox.env")

BASE_URL = environ.get("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
MASTER_REALM = environ.get("KEYCLOAK_MASTER_REALM", "master")
REALM = environ.get("KEYCLOAK_REALM", "netbox-dev")
ADMIN_USER = environ.get("KEYCLOAK_ADMIN_USERNAME", environ.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"))
ADMIN_PASSWORD = environ.get("KEYCLOAK_ADMIN_PASSWORD", environ.get("KC_BOOTSTRAP_ADMIN_PASSWORD", "admin"))
CLIENT_ID = environ.get("KEYCLOAK_CLIENT_ID", "netbox-dev")
CLIENT_SECRET = environ.get("KEYCLOAK_CLIENT_SECRET", environ.get("SOCIAL_AUTH_OIDC_SECRET", "netbox-dev-secret"))
CLIENT_REDIRECT_URIS = environ.get(
    "KEYCLOAK_CLIENT_REDIRECT_URIS",
    environ.get(
        "KEYCLOAK_REDIRECT_URIS",
        "http://localhost:8000/oauth/complete/oidc/ http://netbox.localtest.me:8000/oauth/complete/oidc/",
    ),
)
CLIENT_WEB_ORIGINS = environ.get(
    "KEYCLOAK_CLIENT_WEB_ORIGINS",
    environ.get("KEYCLOAK_WEB_ORIGINS", "http://localhost:8000 http://netbox.localtest.me:8000"),
)
CLIENT_POST_LOGOUT_REDIRECT_URIS = environ.get(
    "KEYCLOAK_CLIENT_POST_LOGOUT_REDIRECT_URIS",
    environ.get("KEYCLOAK_POST_LOGOUT_REDIRECT_URIS", "http://localhost:8000/* http://netbox.localtest.me:8000/*"),
)
LDAP_CONNECTION_URL = environ.get("KEYCLOAK_LDAP_CONNECTION_URL", "ldap://ldap:389")
LDAP_BIND_DN = environ.get("KEYCLOAK_LDAP_BIND_DN", "cn=admin,dc=example,dc=org")
LDAP_BIND_CREDENTIAL = environ.get("KEYCLOAK_LDAP_BIND_CREDENTIAL", "admin")
LDAP_USERS_DN = environ.get("KEYCLOAK_LDAP_USERS_DN", "ou=users,dc=example,dc=org")
LDAP_GROUPS_DN = environ.get("KEYCLOAK_LDAP_GROUPS_DN", "ou=groups,dc=example,dc=org")
LDAP_USE_TRUSTSTORE_SPI = environ.get("KEYCLOAK_LDAP_USE_TRUSTSTORE_SPI", "ldapsOnly")
GOOGLE_CLIENT_ID = environ.get("KEYCLOAK_GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = environ.get("KEYCLOAK_GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_DEFAULT_SCOPE = environ.get("KEYCLOAK_GOOGLE_DEFAULT_SCOPE", "openid profile email")
DEFAULT_USER_SCOPES = {
    "ldap-admin": {
        "dcim_regions": ["region-1"],
        "dcim_sites": ["site-1"],
    },
    "ldap-guest": {
        "dcim_regions": ["region-1"],
        "dcim_sites": ["site-1"],
    },
}


class KeycloakError(RuntimeError):
    pass


def split_env_list(value):
    return [item.strip() for item in str(value or "").replace(",", " ").split() if item.strip()]


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


def update_user(token, user):
    request(
        "PUT",
        f"/admin/realms/{REALM}/users/{quote(user['id'], safe='')}",
        token=token,
        expected=(204,),
        json=user,
    )


def ensure_user_attributes(token, username, attributes):
    users = find_users(token, username)
    if not users:
        return False

    user = users[0]
    existing_attributes = user.get("attributes") or {}
    changed = False
    for name, values in attributes.items():
        values = [str(value) for value in values]
        if existing_attributes.get(name) != values:
            existing_attributes[name] = values
            changed = True
    if not changed:
        return True

    user["attributes"] = existing_attributes
    update_user(token, user)
    return True


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


def ensure_client_settings(token, client_uuid):
    client = get_client_detail(token, client_uuid)
    attributes = dict(client.get("attributes") or {})
    post_logout_uris = split_env_list(CLIENT_POST_LOGOUT_REDIRECT_URIS)

    client.update(
        {
            "clientId": CLIENT_ID,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "clientAuthenticatorType": "client-secret",
            "secret": CLIENT_SECRET,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "redirectUris": split_env_list(CLIENT_REDIRECT_URIS),
            "webOrigins": split_env_list(CLIENT_WEB_ORIGINS),
            "attributes": {
                **attributes,
                "post.logout.redirect.uris": "##".join(post_logout_uris),
            },
        }
    )
    request(
        "PUT",
        f"/admin/realms/{REALM}/clients/{client_uuid}",
        token=token,
        expected=(204,),
        json=client,
    )
    return get_client_detail(token, client_uuid)


def ensure_client_mapper(token, client_uuid, mapper):
    client = get_client_detail(token, client_uuid)
    for item in client.get("protocolMappers") or []:
        if item.get("name") == mapper["name"]:
            mapper = {**item, **mapper}
            request(
                "PUT",
                f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models/{item['id']}",
                token=token,
                expected=(204,),
                json=mapper,
            )
            return
    request(
        "POST",
        f"/admin/realms/{REALM}/clients/{client_uuid}/protocol-mappers/models",
        token=token,
        expected=(201, 204),
        json=mapper,
    )


def ensure_user_attribute_mapper(token, client_uuid, name, user_attribute, claim_name):
    ensure_client_mapper(
        token,
        client_uuid,
        {
            "name": name,
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "user.attribute": user_attribute,
                "claim.name": claim_name,
                "jsonType.label": "String",
                "multivalued": "true",
                "aggregate.attrs": "true",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
            },
        },
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
        updated = {**existing, **component}
        request(
            "PUT",
            f"/admin/realms/{REALM}/components/{existing['id']}",
            token=token,
            expected=(204,),
            json=updated,
        )
        return find_component(
            token,
            component["providerType"],
            component["name"],
            component.get("parentId"),
        )
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
                "connectionUrl": [LDAP_CONNECTION_URL],
                "connectionPooling": ["true"],
                "authType": ["simple"],
                "bindDn": [LDAP_BIND_DN],
                "bindCredential": [LDAP_BIND_CREDENTIAL],
                "usersDn": [LDAP_USERS_DN],
                "usernameLDAPAttribute": ["uid"],
                "rdnLDAPAttribute": ["uid"],
                "uuidLDAPAttribute": ["entryUUID"],
                "userObjectClasses": ["inetOrgPerson, organizationalPerson"],
                "searchScope": ["1"],
                "pagination": ["false"],
                "batchSizeForSync": ["1000"],
                "validatePasswordPolicy": ["false"],
                "trustEmail": ["true"],
                "useTruststoreSpi": [LDAP_USE_TRUSTSTORE_SPI],
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
                "groups.dn": [LDAP_GROUPS_DN],
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
    for attribute_name, ldap_attribute in (
        ("dcim_regions", "businessCategory"),
        ("dcim_sites", "departmentNumber"),
    ):
        ensure_component(
            token,
            {
                "name": attribute_name.replace("_", " "),
                "providerId": "user-attribute-ldap-mapper",
                "providerType": "org.keycloak.storage.ldap.mappers.LDAPStorageMapper",
                "parentId": provider["id"],
                "config": {
                    "mode": ["READ_ONLY"],
                    "ldap.attribute": [ldap_attribute],
                    "user.model.attribute": [attribute_name],
                    "read.only": ["true"],
                    "always.read.value.from.ldap": ["true"],
                    "is.mandatory.in.ldap": ["false"],
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


def get_identity_provider(token, alias):
    response = requests.get(
        f"{BASE_URL}/admin/realms/{REALM}/identity-provider/instances/{quote(alias, safe='')}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise KeycloakError(
            f"GET identity provider {alias} failed with {response.status_code}: {response.text[:1000]}"
        )
    return response.json()


def ensure_identity_provider(token, provider):
    existing = get_identity_provider(token, provider["alias"])
    if existing:
        updated = {**existing, **provider}
        updated["config"] = {**(existing.get("config") or {}), **(provider.get("config") or {})}
        request(
            "PUT",
            f"/admin/realms/{REALM}/identity-provider/instances/{quote(provider['alias'], safe='')}",
            token=token,
            expected=(204,),
            json=updated,
        )
        return get_identity_provider(token, provider["alias"])

    request(
        "POST",
        f"/admin/realms/{REALM}/identity-provider/instances",
        token=token,
        expected=(201, 204),
        json=provider,
    )
    return get_identity_provider(token, provider["alias"])


def ensure_google_identity_provider(token):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None

    return ensure_identity_provider(
        token,
        {
            "alias": "google",
            "displayName": "Google",
            "providerId": "google",
            "enabled": True,
            "trustEmail": True,
            "storeToken": False,
            "addReadTokenRoleOnCreate": False,
            "authenticateByDefault": False,
            "linkOnly": False,
            "firstBrokerLoginFlowAlias": "first broker login",
            "config": {
                "clientId": GOOGLE_CLIENT_ID,
                "clientSecret": GOOGLE_CLIENT_SECRET,
                "defaultScope": GOOGLE_DEFAULT_SCOPE,
                "useJwksUrl": "true",
                "syncMode": "IMPORT",
            },
        },
    )


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
    client = ensure_client_settings(token, client["id"])
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
    ensure_user_attribute_mapper(token, client["id"], "dcim regions", "dcim_regions", "dcim_regions")
    ensure_user_attribute_mapper(token, client["id"], "dcim sites", "dcim_sites", "dcim_sites")
    google_provider = ensure_google_identity_provider(token)

    scoped_users = []
    missing_scoped_users = []
    for username, attributes in DEFAULT_USER_SCOPES.items():
        if ensure_user_attributes(token, username, attributes):
            scoped_users.append(username)
        else:
            missing_scoped_users.append(username)

    print(
        json.dumps(
            {
                "realm": REALM,
                "ldap_provider": provider["id"],
                "ldap_sync": sync_result,
                "client": CLIENT_ID,
                "roles": ["dcim-admin", "dcim-guest"],
                "groups": ["Admin", "Guest"],
                "scope_claims": ["dcim_regions", "dcim_sites"],
                "client_secret_configured": bool(CLIENT_SECRET),
                "client_redirect_uris": split_env_list(CLIENT_REDIRECT_URIS),
                "client_web_origins": split_env_list(CLIENT_WEB_ORIGINS),
                "google_identity_provider": bool(google_provider),
                "google_redirect_uri": f"{BASE_URL}/realms/{REALM}/broker/google/endpoint",
                "scoped_users": scoped_users,
                "missing_scoped_users": missing_scoped_users,
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
