import logging
from urllib.parse import urljoin

import jwt
from django.contrib.auth import get_user_model
from django.core.cache import cache
from jwt import InvalidTokenError, PyJWKClient
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from netbox_smartlock.auth_pipeline import _config_value, sync_keycloak_groups


logger = logging.getLogger("netbox_smartlock.api.authentication")


class KeycloakOIDCAuthentication(BaseAuthentication):
    """
    Authenticate plugin API requests with a Keycloak OIDC Bearer JWT.

    The class intentionally ignores non-JWT Bearer values so NetBox's native API
    token authentication can continue to handle NetBox tokens.
    """

    www_authenticate_realm = "api"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None
        if auth[0].lower() != b"bearer":
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed(
                'Invalid authorization header: Must be in the form "Bearer <token>".'
            )

        token = auth[1].decode("utf-8", errors="ignore")
        if token.count(".") != 2:
            return None

        payload = self.decode_token(token)
        user = self.get_or_create_user(payload)
        sync_keycloak_groups(None, user, payload)
        return user, payload

    def authenticate_header(self, request):
        return f'Bearer realm="{self.www_authenticate_realm}"'

    def decode_token(self, token):
        endpoint = self.issuer
        client_id = self.client_id
        algorithms = self.algorithms
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)
            try:
                return jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=algorithms,
                    audience=client_id,
                    issuer=endpoint,
                )
            except jwt.InvalidAudienceError:
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=algorithms,
                    options={"verify_aud": False},
                    issuer=endpoint,
                )
                if payload.get("azp") != client_id:
                    raise
                return payload
        except InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid Keycloak token: {exc}") from exc
        except Exception as exc:
            logger.exception("Keycloak JWT authentication failed")
            raise exceptions.AuthenticationFailed("Unable to validate Keycloak token") from exc

    def get_or_create_user(self, payload):
        username = payload.get("preferred_username") or payload.get("sub")
        if not username:
            raise exceptions.AuthenticationFailed("Keycloak token does not include a username")

        email = payload.get("email") or ""
        defaults = {
            "email": email,
            "first_name": payload.get("given_name") or "",
            "last_name": payload.get("family_name") or "",
            "is_active": True,
        }
        user, created = get_user_model().objects.get_or_create(username=username, defaults=defaults)
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive")

        changed_fields = []
        for field_name, value in defaults.items():
            if getattr(user, field_name) != value:
                setattr(user, field_name, value)
                changed_fields.append(field_name)
        if changed_fields and not created:
            user.save(update_fields=changed_fields)
        return user

    @property
    def issuer(self):
        endpoint = str(_config_value("SOCIAL_AUTH_OIDC_OIDC_ENDPOINT", "") or "").rstrip("/")
        if not endpoint:
            raise exceptions.AuthenticationFailed("OIDC endpoint is not configured")
        return endpoint

    @property
    def client_id(self):
        client_id = _config_value("SOCIAL_AUTH_OIDC_KEY", "")
        if not client_id:
            raise exceptions.AuthenticationFailed("OIDC client ID is not configured")
        return str(client_id)

    @property
    def algorithms(self):
        algorithms = _config_value("SOCIAL_AUTH_OIDC_JWT_ALGORITHMS", ("RS256",))
        if isinstance(algorithms, str):
            return tuple(item.strip() for item in algorithms.replace(",", " ").split() if item.strip())
        return tuple(str(item).strip() for item in algorithms if str(item).strip())

    @property
    def jwk_client(self):
        cache_key = f"netbox_smartlock:keycloak_jwk_client:{self.issuer}"
        client = cache.get(cache_key)
        if client is None:
            client = PyJWKClient(urljoin(f"{self.issuer}/", "protocol/openid-connect/certs"))
            cache.set(cache_key, client, 300)
        return client
