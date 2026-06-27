from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from social_django.models import UserSocialAuth


PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "outlook.com",
    "yahoo.com",
}
GOOGLE_PROVIDER = "google-oauth2"


def email_domain(email):
    if not email or "@" not in email:
        return ""
    return email.rsplit("@", 1)[1].lower()


def masked_email(email):
    if not email or "@" not in email:
        return ""
    local, domain = email.rsplit("@", 1)
    return f"{local[:3]}***@{domain.lower()}"


class Command(BaseCommand):
    help = "Audit SmartLock Google SSO users, duplicate local emails, and provider links."

    def handle(self, *args, **options):
        User = get_user_model()
        linked_user_ids = set(
            UserSocialAuth.objects.filter(provider=GOOGLE_PROVIDER).values_list("user_id", flat=True)
        )

        users_by_email = defaultdict(list)
        for user in User.objects.exclude(email="").only("id", "username", "email"):
            users_by_email[user.email.lower()].append(user)

        self.stdout.write("Linked SSO users:")
        linked_count = 0
        for social in UserSocialAuth.objects.select_related("user").order_by("provider", "user__username"):
            linked_count += 1
            self.stdout.write(
                f"- provider={social.provider} uid={social.uid} "
                f"user_id={social.user_id} username={social.user.username} "
                f"email={masked_email(social.user.email)}"
            )
        if linked_count == 0:
            self.stdout.write("- none")

        self.stdout.write("")
        self.stdout.write("Local users with email but no Google SSO link:")
        unlinked_count = 0
        for email, users in sorted(users_by_email.items()):
            for user in users:
                if user.id in linked_user_ids:
                    continue
                unlinked_count += 1
                self.stdout.write(f"- user_id={user.id} username={user.username} email={masked_email(email)}")
        if unlinked_count == 0:
            self.stdout.write("- none")

        self.stdout.write("")
        self.stdout.write("Superusers using personal email domains:")
        warning_count = 0
        if not any(field.name == "is_superuser" for field in User._meta.get_fields()):
            self.stdout.write("- skipped: user model has no is_superuser field")
            return

        for user in User.objects.filter(is_superuser=True).exclude(email="").only("id", "username", "email"):
            domain = email_domain(user.email)
            if domain not in PERSONAL_EMAIL_DOMAINS:
                continue
            warning_count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"- user_id={user.id} username={user.username} email={masked_email(user.email)} domain={domain}"
                )
            )
        if warning_count == 0:
            self.stdout.write("- none")
