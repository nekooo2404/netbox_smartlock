from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from social_django.models import UserSocialAuth


class SmartLockSsoManagementCommandTest(TestCase):
    def test_sso_link_requires_matching_confirmation(self):
        get_user_model().objects.create_user(username="admin", email="admin@example.com")

        with self.assertRaises(CommandError):
            call_command(
                "smartlock_sso_link",
                username="admin",
                confirm_username="wrong",
                provider="google-oauth2",
                uid="google-sub",
            )

    def test_sso_link_creates_sanitized_association(self):
        user = get_user_model().objects.create_user(username="admin", email="admin@example.com")

        call_command(
            "smartlock_sso_link",
            username="admin",
            confirm_username="admin",
            provider="google-oauth2",
            uid="google-sub",
        )

        social = UserSocialAuth.objects.get(user=user, provider="google-oauth2", uid="google-sub")
        self.assertEqual(social.extra_data, {})

    def test_sso_audit_masks_email_and_lists_links(self):
        user = get_user_model().objects.create_user(username="guest", email="guest@gmail.com")
        UserSocialAuth.objects.create(user=user, provider="google-oauth2", uid="google-sub", extra_data={})
        output = StringIO()

        call_command("smartlock_sso_audit", stdout=output)

        text = output.getvalue()
        self.assertIn("provider=google-oauth2", text)
        self.assertIn("gue***@gmail.com", text)
        self.assertNotIn("guest@gmail.com", text)

    def test_sso_audit_lists_local_user_without_google_link(self):
        get_user_model().objects.create_user(username="admin", email="admin@gmail.com")
        output = StringIO()

        call_command("smartlock_sso_audit", stdout=output)

        text = output.getvalue()
        self.assertIn("Local users with email but no Google SSO link:", text)
        self.assertIn("username=admin", text)
        self.assertIn("adm***@gmail.com", text)
