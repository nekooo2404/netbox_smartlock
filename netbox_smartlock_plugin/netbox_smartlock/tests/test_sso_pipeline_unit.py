import sys
import types
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from django.conf import settings

netbox_module = types.ModuleType("netbox")
plugins_module = types.ModuleType("netbox.plugins")
plugins_module.PluginConfig = type("PluginConfig", (), {})
sys.modules.setdefault("netbox", netbox_module)
sys.modules.setdefault("netbox.plugins", plugins_module)

if not settings.configured:
    settings.configure(
        SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=["company.com"],
        SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL=True,
        SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=True,
    )

PIPELINE_PATH = Path(__file__).resolve().parents[1] / "sso_pipeline.py"
spec = importlib.util.spec_from_file_location("sso_pipeline_under_test", PIPELINE_PATH)
sso_pipeline = importlib.util.module_from_spec(spec)
sys.modules["sso_pipeline_under_test"] = sso_pipeline
spec.loader.exec_module(sso_pipeline)

block_duplicate_google_email = sso_pipeline.block_duplicate_google_email
validate_google_identity = sso_pipeline.validate_google_identity


class GoogleSsoPipelineUnitTest(TestCase):
    def setUp(self):
        self.backend = Mock(name="backend")
        self.backend.name = "google-oauth2"

    def test_domain_validation_rejects_unverified_email(self):
        with self.assertRaises(Exception):
            validate_google_identity(
                self.backend,
                details={"email": "user@company.com"},
                response={"email_verified": False, "hd": "company.com"},
            )

    def test_domain_validation_rejects_wrong_domain(self):
        with self.assertRaises(Exception):
            validate_google_identity(
                self.backend,
                details={"email": "user@example.com"},
                response={"email_verified": True, "hd": "example.com"},
            )

    def test_workspace_validation_accepts_verified_identity(self):
        result = validate_google_identity(
            self.backend,
            details={"email": "user@company.com"},
            response={"email_verified": True, "hd": "company.com"},
        )

        self.assertIsNone(result)

    def test_duplicate_email_blocks_unassociated_user(self):
        existing_user = Mock(pk=1, username="admin", is_staff=True, is_superuser=True)
        queryset = Mock()
        queryset.only.return_value.first.return_value = existing_user
        manager = Mock()
        manager.filter.return_value = queryset
        user_model = Mock(objects=manager)
        user_model._meta.get_fields.return_value = [
            SimpleNamespace(name="pk"),
            SimpleNamespace(name="username"),
            SimpleNamespace(name="is_staff"),
            SimpleNamespace(name="is_superuser"),
        ]

        with patch.object(sso_pipeline, "get_user_model", return_value=user_model):
            with self.assertRaises(Exception):
                block_duplicate_google_email(
                    self.backend,
                    details={"email": "user@company.com"},
                    response={"email_verified": True},
                    social=None,
                )


if __name__ == "__main__":
    import unittest

    unittest.main()
