from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from social_django.models import UserSocialAuth


class Command(BaseCommand):
    help = "Safely link an existing local user to a Google SSO identity."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Existing local NetBox username to link.")
        parser.add_argument("--provider", default="google-oauth2", help="SSO provider, normally google-oauth2.")
        parser.add_argument("--uid", required=True, help="Provider UID/sub claim for this user.")
        parser.add_argument(
            "--confirm-username",
            required=True,
            help="Must exactly match --username to prevent accidental privileged linking.",
        )
        parser.add_argument(
            "--replace-existing",
            action="store_true",
            help="Move this provider UID from another user to the target user.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        provider = options["provider"]
        uid = options["uid"]
        confirm_username = options["confirm_username"]

        if provider != "google-oauth2":
            raise CommandError("Only provider=google-oauth2 is supported by this deployment.")
        if username != confirm_username:
            raise CommandError("--confirm-username must exactly match --username.")

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User does not exist: {username}") from exc

        existing_for_user = UserSocialAuth.objects.filter(provider=provider, user=user).exclude(uid=uid).first()
        if existing_for_user:
            raise CommandError(
                f"User {username} is already linked to provider={provider} uid={existing_for_user.uid}."
            )

        existing_for_uid = UserSocialAuth.objects.filter(provider=provider, uid=uid).select_related("user").first()
        if existing_for_uid and existing_for_uid.user_id != user.id:
            if not options["replace_existing"]:
                raise CommandError(
                    "This provider UID is already linked to another user. "
                    "Use --replace-existing only after verifying ownership."
                )
            existing_for_uid.delete()

        social, created = UserSocialAuth.objects.get_or_create(
            user=user,
            provider=provider,
            uid=uid,
            defaults={"extra_data": {}},
        )
        if not created and social.extra_data:
            social.extra_data = {}
            social.save(update_fields=["extra_data"])

        action = "created" if created else "verified"
        self.stdout.write(
            self.style.SUCCESS(
                f"SSO link {action}: username={username} provider={provider} uid={uid}"
            )
        )
