import logging

from django.conf import settings
from django.contrib.auth import get_user_model

try:
    from social_core.exceptions import AuthForbidden
    from social_core.pipeline.social_auth import load_extra_data as social_load_extra_data
except Exception:  # pragma: no cover - only used when social-auth-core is absent in lightweight tooling
    class AuthForbidden(Exception):
        def __init__(self, backend=None, *args):
            super().__init__(*args or ("Authentication forbidden",))

    social_load_extra_data = None


logger = logging.getLogger("netbox_smartlock.sso")


GOOGLE_BACKEND_NAME = "google-oauth2"


def validate_google_identity(backend, details=None, response=None, **kwargs):
    if not _is_google_backend(backend):
        return None

    details = details or {}
    response = response or {}
    email = _email_from(details, response)

    if not email:
        _reject(backend, "missing_email")

    if _setting_bool("SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL", True):
        if not _is_truthy(response.get("email_verified")):
            _reject(backend, "email_not_verified", email=email)

    allowed_domains = _setting_list("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS")
    domain = _email_domain(email)
    if allowed_domains and domain not in allowed_domains:
        _reject(backend, "email_domain_rejected", email=email, domain=domain)

    if _setting_bool("SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN", False):
        hosted_domain = _normalize_domain(response.get("hd"))
        allowed_hosted_domains = _setting_list("SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS")
        allowed_hosted_domains = allowed_hosted_domains or allowed_domains

        if not hosted_domain:
            _reject(backend, "hosted_domain_missing", email=email, domain=domain)
        if allowed_hosted_domains and hosted_domain not in allowed_hosted_domains:
            _reject(backend, "hosted_domain_rejected", email=email, domain=domain, hosted_domain=hosted_domain)

    return None


def block_duplicate_google_email(backend, details=None, response=None, social=None, **kwargs):
    if not _is_google_backend(backend) or social is not None:
        return None

    details = details or {}
    response = response or {}
    email = _email_from(details, response)
    if not email:
        return None

    User = get_user_model()
    selected_fields = _existing_user_fields(User)
    existing_user = User.objects.filter(email__iexact=email).only(*selected_fields).first()
    if existing_user is None:
        return None

    _reject(
        backend,
        "duplicate_email_without_social_association",
        email=email,
        user_id=existing_user.pk,
        username=existing_user.username,
        is_staff=getattr(existing_user, "is_staff", False),
        is_superuser=getattr(existing_user, "is_superuser", False),
    )

    return None


def audit_google_sso_success(backend, details=None, response=None, user=None, is_new=False, **kwargs):
    if not _is_google_backend(backend) or user is None:
        return None

    details = details or {}
    response = response or {}
    email = _email_from(details, response) or getattr(user, "email", "")
    audit_context = {
        "user_id": getattr(user, "pk", None),
        "username": getattr(user, "username", ""),
        "email_domain": _email_domain(email),
        "hosted_domain": _normalize_domain(response.get("hd")),
    }

    if is_new:
        logger.info("Google SSO user auto-created", extra=audit_context)
    logger.info("Google SSO login success", extra=audit_context)

    return None


def load_sanitized_google_extra_data(
    backend,
    details=None,
    response=None,
    uid=None,
    user=None,
    social=None,
    *args,
    **kwargs,
):
    if not _is_google_backend(backend):
        if social_load_extra_data is None:
            return None
        return social_load_extra_data(
            backend,
            details=details,
            response=response,
            uid=uid,
            user=user,
            social=social,
            *args,
            **kwargs,
        )

    if social is None:
        return None

    clean_response = _sanitize_google_response(response or {})
    extra_data = backend.extra_data(user, uid, clean_response, details or {}, *args, **kwargs)
    social.set_extra_data(_sanitize_google_response(extra_data or {}))
    return None


def _is_google_backend(backend):
    return getattr(backend, "name", "") == GOOGLE_BACKEND_NAME


def _sanitize_google_response(response):
    token_keys = {
        "access_token",
        "authorization_code",
        "code",
        "expires",
        "expires_in",
        "id_token",
        "refresh_token",
        "token",
        "token_type",
    }
    return {key: value for key, value in response.items() if key not in token_keys}


def _existing_user_fields(User):
    optional_fields = ("is_staff", "is_superuser")
    existing_field_names = {field.name for field in User._meta.get_fields()}
    return ["pk", "username", *(field for field in optional_fields if field in existing_field_names)]


def _email_from(details, response):
    return (details.get("email") or response.get("email") or "").strip().lower()


def _email_domain(email):
    if "@" not in email:
        return ""
    return _normalize_domain(email.rsplit("@", 1)[1])


def _normalize_domain(value):
    return str(value or "").strip().lower().lstrip("@")


def _setting_list(name):
    value = getattr(settings, name, [])
    if value is None:
        return set()
    if isinstance(value, str):
        values = value.split()
    else:
        values = value
    return {_normalize_domain(item) for item in values if _normalize_domain(item)}


def _setting_bool(name, default):
    value = getattr(settings, name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_truthy(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _reject(backend, reason, **context):
    safe_context = {key: value for key, value in context.items() if key != "email"}
    if "email" in context:
        safe_context["email_domain"] = _email_domain(context["email"])
    safe_context["reason"] = reason
    logger.warning(
        "Google SSO login rejected reason=%s email_domain=%s user_id=%s username=%s",
        reason,
        safe_context.get("email_domain", ""),
        safe_context.get("user_id", ""),
        safe_context.get("username", ""),
        extra=safe_context,
    )
    raise AuthForbidden(backend)
