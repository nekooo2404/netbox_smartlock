from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

import netbox_smartlock.sso_pipeline as sso_pipeline
from netbox_smartlock.sso_pipeline import (
    block_duplicate_google_email,
    load_sanitized_google_extra_data,
    validate_google_identity,
)


class GoogleSsoPipelineTest(TestCase):
    def setUp(self):
        self.backend = Mock(name="backend")
        self.backend.name = "google-oauth2"

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=["company.com"])
    def test_rejects_unverified_email(self):
        with self.assertRaises(Exception):
            validate_google_identity(
                self.backend,
                details={"email": "user@company.com"},
                response={"email_verified": False},
            )

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=["company.com"])
    def test_rejects_email_outside_allowed_domain(self):
        with self.assertRaises(Exception):
            validate_google_identity(
                self.backend,
                details={"email": "user@example.com"},
                response={"email_verified": True},
            )

    @override_settings(
        SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=["company.com"],
        SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=True,
    )
    def test_rejects_missing_hosted_domain_when_required(self):
        with self.assertRaises(Exception):
            validate_google_identity(
                self.backend,
                details={"email": "user@company.com"},
                response={"email_verified": True},
            )

    @override_settings(
        SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=["company.com"],
        SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=True,
    )
    def test_accepts_verified_workspace_identity(self):
        result = validate_google_identity(
            self.backend,
            details={"email": "user@company.com"},
            response={"email_verified": True, "hd": "company.com"},
        )

        self.assertIsNone(result)

    def test_duplicate_email_without_social_association_is_blocked(self):
        user = get_user_model().objects.create_user(username="admin", email="user@company.com")
        if hasattr(user, "is_staff"):
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        with self.assertRaises(Exception):
            block_duplicate_google_email(
                self.backend,
                details={"email": "user@company.com"},
                response={"email_verified": True},
                social=None,
            )

    def test_existing_social_association_is_allowed(self):
        get_user_model().objects.create_user(username="guest", email="user@company.com")

        result = block_duplicate_google_email(
            self.backend,
            details={"email": "user@company.com"},
            response={"email_verified": True},
            social=object(),
        )

        self.assertIsNone(result)

    def test_rejection_logs_reason_without_raw_email(self):
        with patch("netbox_smartlock.sso_pipeline.logger.warning") as warning:
            with self.assertRaises(Exception):
                validate_google_identity(
                    self.backend,
                    details={"email": "user@example.com"},
                    response={"email_verified": False},
                )

        _, kwargs = warning.call_args
        self.assertNotIn("email", kwargs["extra"])
        self.assertEqual(kwargs["extra"]["email_domain"], "example.com")

    def test_duplicate_email_rejection_does_not_require_auth_for_associated_user(self):
        field = Mock()
        field.name = "username"
        user_meta = Mock()
        user_meta.get_fields.return_value = [field]
        existing_user = Mock(pk=1, username="admin")
        del existing_user.is_staff
        del existing_user.is_superuser
        queryset = Mock()
        queryset.only.return_value.first.return_value = existing_user
        manager = Mock()
        manager.filter.return_value = queryset
        user_model = Mock(objects=manager, _meta=user_meta)

        with patch.object(sso_pipeline, "get_user_model", return_value=user_model):
            with self.assertRaises(Exception):
                block_duplicate_google_email(
                    self.backend,
                    details={"email": "user@company.com"},
                    response={"email_verified": True},
                    social=None,
                )

        queryset.only.assert_called_once_with("pk", "username")

    def test_google_extra_data_does_not_store_tokens(self):
        backend = Mock()
        backend.name = "google-oauth2"
        backend.extra_data.return_value = {
            "access_token": "secret-access-token",
            "email": "user@company.com",
            "expires": 3600,
            "id_token": "secret-id-token",
            "refresh_token": "secret-refresh-token",
        }
        social = Mock()

        load_sanitized_google_extra_data(
            backend,
            details={},
            response={
                "access_token": "secret-access-token",
                "email": "user@company.com",
                "expires": 3600,
                "id_token": "secret-id-token",
                "refresh_token": "secret-refresh-token",
            },
            social=social,
            user=Mock(),
            uid="google-sub",
        )

        response_arg = backend.extra_data.call_args.args[2]
        self.assertEqual(response_arg, {"email": "user@company.com"})
        social.set_extra_data.assert_called_once_with({"email": "user@company.com"})
