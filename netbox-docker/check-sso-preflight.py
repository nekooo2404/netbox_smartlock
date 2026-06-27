#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_BACKENDS = ("social_core.backends.google.GoogleOAuth2",)
REQUIRED_GOOGLE_SCOPES = {"openid", "email", "profile"}
GOOGLE_CALLBACK = "http://localhost:8000/oauth/complete/google-oauth2/"
GOOGLE_CALLBACK_PATH = "/oauth/complete/google-oauth2/"
PLACEHOLDER_MARKERS = ("<", ">", "replace-with", "your_", "change-me")
LEGACY_TERMS = (
    "KEY" + "CLOAK",
    "Key" + "cloak",
    "key" + "cloak",
    "OK" + "TA",
    "Ok" + "ta",
    "o" + "kta",
    "SOCIAL_AUTH_" + "O" + "IDC",
    "SOCIAL_AUTH_" + "OK" + "TA",
    "open_id" + "_connect",
    "o" + "kta_" + "openidconnect",
    "O" + "kta" + "OpenIdConnect",
    "dcim_" + "regions",
    "dcim_" + "sites",
    "docker-compose." + "key" + "cloak",
    "netbox_smartlock." + "auth_pipeline",
)


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip().lstrip("\ufeff")] = value.strip().strip('"').strip("'")
    return values


def is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def check_secret_file(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"Missing Docker secret file for {label}: {path}")
        return
    value = path.read_text(encoding="utf-8").strip()
    if is_placeholder(value):
        errors.append(f"Docker secret file for {label} is empty or still a placeholder: {path}")


def tracked_text_files(root: Path):
    ignored_dirs = {".git", ".understand-anything", "__pycache__", ".pytest_cache", "media", "staticfiles"}
    allowed_suffixes = {
        "",
        ".env",
        ".example",
        ".md",
        ".py",
        ".ps1",
        ".txt",
        ".yml",
        ".yaml",
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_dirs for part in path.parts):
            continue
        if path.name == Path(__file__).name:
            continue
        if "secrets" in path.parts:
            continue
        if path.suffix.lower() not in allowed_suffixes:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight-check NetBox Google SSO configuration.")
    parser.add_argument("--env-file", default="env/netbox.env", help="Path relative to netbox-docker/")
    parser.add_argument("--redis-env-file", default="env/redis.env", help="Path relative to netbox-docker/")
    parser.add_argument("--redis-cache-env-file", default="env/redis-cache.env", help="Path relative to netbox-docker/")
    parser.add_argument("--secrets-dir", default="secrets", help="Path relative to netbox-docker/")
    parser.add_argument("--production", action="store_true", help="Apply production HTTPS checks.")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Expected NetBox base URL.")
    args = parser.parse_args()

    netbox_docker = Path(__file__).resolve().parent
    repo_root = netbox_docker.parent
    env_file = (netbox_docker / args.env_file).resolve()
    redis_env_file = (netbox_docker / args.redis_env_file).resolve()
    redis_cache_env_file = (netbox_docker / args.redis_cache_env_file).resolve()
    secrets_dir = (netbox_docker / args.secrets_dir).resolve()
    errors: list[str] = []

    if not env_file.exists():
        errors.append(f"Missing env file: {env_file}")
        env = {}
    else:
        env = parse_env(env_file)
    redis_env = parse_optional_env(redis_env_file, errors)
    redis_cache_env = parse_optional_env(redis_cache_env_file, errors)

    if env.get("REMOTE_AUTH_ENABLED") != "True":
        errors.append("REMOTE_AUTH_ENABLED must be True.")
    if env.get("REMOTE_AUTH_AUTO_CREATE_USER") != "True":
        errors.append("REMOTE_AUTH_AUTO_CREATE_USER must be True.")
    if "Guest" not in env.get("REMOTE_AUTH_DEFAULT_GROUPS", "").split():
        errors.append("REMOTE_AUTH_DEFAULT_GROUPS must include Guest.")

    backends = env.get("REMOTE_AUTH_BACKEND", "").split()
    if set(backends) != set(REQUIRED_BACKENDS):
        errors.append("REMOTE_AUTH_BACKEND must contain exactly the GoogleOAuth2 backend.")

    if is_placeholder(env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY")):
        errors.append("Missing or placeholder SOCIAL_AUTH_GOOGLE_OAUTH2_KEY.")
    google_scopes = set(env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE", "").split())
    if not REQUIRED_GOOGLE_SCOPES.issubset(google_scopes):
        errors.append("SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE must include: openid email profile.")
    if "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET" in env:
        errors.append("Remove SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET from env; use Docker secret google_oauth2_secret.")
    if has_unescaped_dollar(env.get("SECRET_KEY", "")):
        errors.append("SECRET_KEY contains an unescaped '$'. Use '$$' in Docker Compose env files.")
    if env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL", "True") != "True":
        errors.append("SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL must be True.")

    check_redis_passwords(env, redis_env, redis_cache_env, errors)

    extra_args = parse_key_value_list(env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS", ""))
    if extra_args.get("prompt") != "select_account":
        errors.append("SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS must include prompt=select_account.")

    allowed_domains = env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS", "").split()
    if env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN") == "True":
        allowed_hosted_domains = env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS", "").split()
        if not (allowed_domains or allowed_hosted_domains):
            errors.append("Hosted-domain enforcement requires an allowed Google domain.")
        if "hd" not in extra_args:
            errors.append("Workspace mode should include hd=<domain> in Google auth extra arguments.")

    check_secret_file(secrets_dir / "google_oauth2_secret.txt", "Google OAuth2", errors)

    expected_callback = callback_for_base_url(args.base_url)
    for path in (repo_root / "README.md", netbox_docker / "README.md", env_file):
        if not path.exists():
            errors.append(f"Missing file for callback checklist: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if args.production:
            if expected_callback not in text:
                errors.append(f"Missing production callback {expected_callback} in {path}")
        elif GOOGLE_CALLBACK not in text:
            errors.append(f"Missing callback {GOOGLE_CALLBACK} in {path}")

    if args.production:
        check_production_settings(env, args.base_url, expected_callback, errors)

    for path in tracked_text_files(repo_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for term in LEGACY_TERMS:
            if term in text:
                errors.append(f"Legacy SSO term '{term}' remains in {path}")

    if errors:
        print("SSO preflight failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SSO preflight passed.")
    return 0


def parse_key_value_list(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in value.split():
        if "=" not in item:
            continue
        key, item_value = item.split("=", 1)
        result[key] = item_value
    return result


def parse_optional_env(path: Path, errors: list[str]) -> dict[str, str]:
    if not path.exists():
        errors.append(f"Missing env file: {path}")
        return {}
    return parse_env(path)


def check_redis_passwords(
    netbox_env: dict[str, str],
    redis_env: dict[str, str],
    redis_cache_env: dict[str, str],
    errors: list[str],
) -> None:
    redis_password = netbox_env.get("REDIS_PASSWORD")
    service_redis_password = redis_env.get("REDIS_PASSWORD")
    if redis_password != service_redis_password:
        errors.append("REDIS_PASSWORD in netbox.env must match REDIS_PASSWORD in redis.env.")

    redis_cache_password = netbox_env.get("REDIS_CACHE_PASSWORD")
    service_redis_cache_password = redis_cache_env.get("REDIS_PASSWORD")
    if redis_cache_password != service_redis_cache_password:
        errors.append("REDIS_CACHE_PASSWORD in netbox.env must match REDIS_PASSWORD in redis-cache.env.")


def callback_for_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + GOOGLE_CALLBACK_PATH


def check_production_settings(env: dict[str, str], base_url: str, expected_callback: str, errors: list[str]) -> None:
    parsed_base_url = urlparse(base_url)
    if parsed_base_url.scheme != "https":
        errors.append("--production requires --base-url to use https://.")
    if parsed_base_url.hostname in {"localhost", "127.0.0.1", "::1"}:
        errors.append("--production must not use localhost or loopback base URL.")

    url_fields = {
        "CORS_ORIGIN_WHITELIST": env.get("CORS_ORIGIN_WHITELIST", ""),
        "CSRF_TRUSTED_ORIGINS": env.get("CSRF_TRUSTED_ORIGINS", ""),
        "LOGOUT_REDIRECT_URL": env.get("LOGOUT_REDIRECT_URL", ""),
    }
    for name, value in url_fields.items():
        if "localhost" in value or "127.0.0.1" in value or "http://" in value:
            errors.append(f"{name} must use the production https:// domain, not localhost/http.")

    if env.get("SECURE_SSL_REDIRECT") != "True":
        errors.append("SECURE_SSL_REDIRECT must be True in production.")
    if int_or_zero(env.get("SECURE_HSTS_SECONDS")) <= 0:
        errors.append("SECURE_HSTS_SECONDS must be greater than 0 in production.")
    if env.get("SESSION_COOKIE_SECURE") != "True":
        errors.append("SESSION_COOKIE_SECURE must be True in production.")
    if env.get("CSRF_COOKIE_SECURE") != "True":
        errors.append("CSRF_COOKIE_SECURE must be True in production.")
    if env.get("SESSION_COOKIE_SAMESITE", "Lax") != "Lax":
        errors.append("SESSION_COOKIE_SAMESITE should be Lax in production.")
    if env.get("CSRF_COOKIE_SAMESITE", "Lax") != "Lax":
        errors.append("CSRF_COOKIE_SAMESITE should be Lax in production.")
    if not env.get("SECURE_PROXY_SSL_HEADER"):
        errors.append("SECURE_PROXY_SSL_HEADER should be set when NetBox is behind a TLS reverse proxy.")
    if expected_callback.startswith("http://"):
        errors.append("Google production callback must use https://.")
    if not env.get("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS", "").split():
        errors.append("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS must be set in production.")


def int_or_zero(value: str | None) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0


def has_unescaped_dollar(value: str) -> bool:
    index = 0
    while index < len(value):
        if value[index] != "$":
            index += 1
            continue
        if index + 1 < len(value) and value[index + 1] == "$":
            index += 2
            continue
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
