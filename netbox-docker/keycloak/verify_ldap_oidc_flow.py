#!/usr/bin/env python3
import json
import re
import sys
from html import unescape
from os import environ
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

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

KEYCLOAK_BASE_URL = environ.get(
    "KEYCLOAK_VERIFY_BASE_URL",
    environ.get("KEYCLOAK_BASE_URL", "http://keycloak.localtest.me:8080"),
).rstrip("/")
NETBOX_BASE_URL = environ.get("NETBOX_VERIFY_BASE_URL", "http://localhost:8000").rstrip("/")
REALM = environ.get("KEYCLOAK_REALM", "netbox-dev")
CLIENT_ID = environ.get("KEYCLOAK_CLIENT_ID", "netbox-dev")
CLIENT_SECRET = environ.get("KEYCLOAK_CLIENT_SECRET", environ.get("SOCIAL_AUTH_OIDC_SECRET", "netbox-dev-secret"))
REDIRECT_URI = environ.get("KEYCLOAK_VERIFY_REDIRECT_URI", f"{NETBOX_BASE_URL}/oauth/complete/oidc/")
USERS = (
    ("ldap-admin", environ.get("KEYCLOAK_VERIFY_LDAP_ADMIN_PASSWORD", "admin"), "/api/plugins/smartlock/asset-groups/"),
    ("ldap-guest", environ.get("KEYCLOAK_VERIFY_LDAP_GUEST_PASSWORD", "guest"), "/api/plugins/smartlock/access-requests/"),
)


def fail(message):
    raise RuntimeError(message)


def login_and_get_token(username, password):
    session = requests.Session()
    auth_url = f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/auth?" + urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": f"state-{username}",
            "nonce": f"nonce-{username}",
        }
    )
    login_response = session.get(auth_url, timeout=30)
    login_response.raise_for_status()

    match = re.search(r'<form[^>]+action="([^"]+)"', login_response.text)
    if not match:
        fail(f"Keycloak login form was not found for {username}")

    action = unescape(match.group(1))
    auth_response = session.post(
        action,
        data={"username": username, "password": password, "credentialId": ""},
        allow_redirects=False,
        timeout=30,
    )
    if auth_response.status_code != 302:
        fail(f"Keycloak login failed for {username}: {auth_response.status_code}")

    location = auth_response.headers.get("Location", "")
    code = parse_qs(urlparse(location).query).get("code", [None])[0]
    if not code:
        fail(f"Keycloak did not return an authorization code for {username}")

    token_response = session.post(
        f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=30,
    )
    token_response.raise_for_status()
    return token_response.json()["access_token"]


def verify_user(username, password, api_path):
    token = login_and_get_token(username, password)
    userinfo_response = requests.get(
        f"{KEYCLOAK_BASE_URL}/realms/{REALM}/protocol/openid-connect/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    userinfo_response.raise_for_status()
    userinfo = userinfo_response.json()

    missing_claims = [
        claim_name
        for claim_name in ("groups", "roles", "dcim_regions", "dcim_sites")
        if not userinfo.get(claim_name)
    ]
    if missing_claims:
        fail(f"{username} token is missing required claims: {', '.join(missing_claims)}")

    api_response = requests.get(
        f"{NETBOX_BASE_URL}{api_path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if api_response.status_code != 200:
        fail(f"NetBox API {api_path} failed for {username}: {api_response.status_code} {api_response.text[:500]}")

    return {
        "username": username,
        "groups": userinfo.get("groups"),
        "roles": userinfo.get("roles"),
        "dcim_regions": userinfo.get("dcim_regions"),
        "dcim_sites": userinfo.get("dcim_sites"),
        "api_path": api_path,
        "api_status": api_response.status_code,
    }


def main():
    results = [verify_user(username, password, api_path) for username, password, api_path in USERS]
    print(json.dumps({"ok": True, "results": results}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        sys.exit(1)
