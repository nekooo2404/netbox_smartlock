# netbox-docker

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/netbox-community/netbox-docker)][github-release]
[![GitHub stars](https://img.shields.io/github/stars/netbox-community/netbox-docker)][github-stargazers]
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/netbox-community/netbox-docker)
![Github release workflow](https://img.shields.io/github/actions/workflow/status/netbox-community/netbox-docker/release.yml?branch=release)
![Docker Pulls](https://img.shields.io/docker/pulls/netboxcommunity/netbox)
[![GitHub license](https://img.shields.io/github/license/netbox-community/netbox-docker)][netbox-docker-license]

[The GitHub repository][netbox-docker-github] houses the components needed to build NetBox as a container.
Images are built regularly using the code in that repository
and are pushed to [Docker Hub][netbox-dockerhub],
[Quay.io][netbox-quayio] and [GitHub Container Registry][netbox-ghcr].
_NetBox Docker_ is a project developed and maintained by the _NetBox_ community.

Do you have any questions?
Before opening an issue on GitHub,
please join [our Slack][netbox-docker-slack]
and ask for help in the [`#netbox-docker`][netbox-docker-slack-channel] channel,
or start a new [GitHub Discussion][github-discussions].

[github-stargazers]: https://github.com/netbox-community/netbox-docker/stargazers
[github-release]: https://github.com/netbox-community/netbox-docker/releases
[netbox-dockerhub]: https://hub.docker.com/r/netboxcommunity/netbox/
[netbox-quayio]: https://quay.io/repository/netboxcommunity/netbox
[netbox-ghcr]: https://github.com/netbox-community/netbox-docker/pkgs/container/netbox
[netbox-docker-github]: https://github.com/netbox-community/netbox-docker/
[netbox-docker-slack]: https://join.slack.com/t/netdev-community/shared_invite/zt-mtts8g0n-Sm6Wutn62q_M4OdsaIycrQ
[netbox-docker-slack-channel]: https://netdev-community.slack.com/archives/C01P0GEVBU7
[netbox-slack-channel]: https://netdev-community.slack.com/archives/C01P0FRSXRV
[netbox-docker-license]: https://github.com/netbox-community/netbox-docker/blob/release/LICENSE
[github-discussions]: https://github.com/netbox-community/netbox-docker/discussions

## Quickstart

To get _NetBox Docker_ up and running run the following commands.
There is a more complete [_Getting Started_ guide on our wiki][wiki-getting-started] which explains every step.

```bash
git clone -b release https://github.com/netbox-community/netbox-docker.git
cd netbox-docker
# Copy the example override file
cp docker-compose.override.yml.example docker-compose.override.yml
# Read and edit the file to your liking
docker compose pull
docker compose up
```

The whole application will be available after a few minutes.
Open the URL `http://0.0.0.0:8000/` in a web-browser.
You should see the NetBox homepage.

## Google SSO

This repository uses the official NetBox Google OAuth2 authentication flow.
No extra identity overlay is included.

Official NetBox references:

- Google: https://netboxlabs.com/docs/netbox/administration/authentication/google/

Google OAuth2 callback URIs:

```text
http://localhost:8000/oauth/complete/google-oauth2/
```

Google OAuth does not allow raw IP redirect URIs except `127.0.0.1`.
Use `localhost` for development and a real HTTPS domain for production.

Relevant NetBox environment variables:

```env
REMOTE_AUTH_ENABLED=True
REMOTE_AUTH_AUTO_CREATE_USER=True
REMOTE_AUTH_BACKEND=social_core.backends.google.GoogleOAuth2
REMOTE_AUTH_DEFAULT_GROUPS=Guest
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=<google-client-id>
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE=openid email profile
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_VERIFIED_EMAIL=True
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=False
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS=
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS=prompt=select_account
```

The `openid email profile` scope enables OpenID Connect on Google OAuth2 and lets NetBox receive the user's basic identity claims.
For Google Workspace, set the allowed domains and hosted-domain enforcement:

```env
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS=company.com
SOCIAL_AUTH_GOOGLE_OAUTH2_REQUIRE_HOSTED_DOMAIN=True
SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_HOSTED_DOMAINS=company.com
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS=prompt=select_account hd=company.com
```

The `hd=company.com` argument is only a Google UI hint. The backend pipeline still validates `email_verified`, the email domain, and the `hd` claim.

Do not store OAuth client secrets in `env/netbox.env`. Put them in local
Docker secret files instead:

```text
secrets/google_oauth2_secret.txt
```

It is mounted into the container as:

```text
/run/secrets/google_oauth2_secret
```

Google appears on the normal NetBox `/login/` page.
NetBox creates or links the local user after SSO login. New SSO users are added
to `Guest` by default; grant `Admin` manually in NetBox when required.

Production policy:

- Require one verified corporate Google email per person.
- Keep group and permission management in NetBox with `Admin`, `Guest`, and
  ObjectPermission. Do not add custom provider group sync until the business
  requirement is explicit.
- Keep local NetBox login enabled and keep at least one local superuser as a
  break-glass account.

Bootstrap SmartLock RBAC:

```powershell
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_bootstrap_rbac
```

Audit SSO users and manually link a verified Google identity only when needed:

```powershell
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_sso_audit
docker compose exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_sso_link --username admin --confirm-username admin --provider google-oauth2 --uid <google-sub-claim>
```

Use `smartlock_sso_link` only after an administrator has verified that the Google
`sub` claim belongs to the intended local NetBox user. The command does not link
by email automatically because that can accidentally grant local admin access.

SSO troubleshooting:

- `Single sign-on failed`: inspect `docker compose logs netbox` for
  `Google SSO login rejected reason=...`.
- `duplicate_email_without_social_association`: Google email matches a local
  NetBox user, but no social-auth link exists yet. Use a different Google
  account, change the local user's email, or link manually with
  `smartlock_sso_link`.
- `email_not_verified`: Google did not mark the email as verified.
- `email_domain_rejected`: email is outside
  `SOCIAL_AUTH_GOOGLE_OAUTH2_ALLOWED_DOMAINS`.
- `hosted_domain_missing`: Workspace mode is enabled but Google did not return
  the `hd` claim.
- `hosted_domain_rejected`: Google returned an `hd` claim outside the allowed
  hosted domains.
- Google OAuth tokens are not stored in `social_django_usersocialauth.extra_data`;
  the pipeline keeps only non-sensitive metadata.

After bootstrap:

- `Admin` manages AssetGroup, Asset, SmartLock, and access-request workflow.
- `Guest` manages only their own requests and request persons.
- Region/Site/Location/Rack visibility is controlled by NetBox ObjectPermission.

Production hardening:

- Use HTTPS public domains for NetBox and Google.
- Update `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, Google redirect URIs,
  and `LOGOUT_REDIRECT_URL`.
- Enable `SECURE_SSL_REDIRECT=True` and HSTS after TLS is in place.
- Replace all dev secrets and use Docker/Kubernetes secrets for `SECRET_KEY`,
  database/Redis passwords, and Google client secret.
- Keep NetBox's normal `/login/` page enabled when following the official
  NetBox OAuth examples. OAuth provider buttons are rendered beside the local
  login form.

Run the local SSO preflight before starting NetBox:

```bash
python check-sso-preflight.py
```

Run the production preflight before deployment:

```bash
python check-sso-preflight.py --production --base-url https://netbox.example.com
```

Google Console checklist:

- Use OAuth app type `Internal` for Google Workspace.
- Development redirect URI: `http://localhost:8000/oauth/complete/google-oauth2/`.
- Production redirect URI: `https://netbox.example.com/oauth/complete/google-oauth2/`.
- Do not use raw IP redirect URIs except `127.0.0.1` for development.
- Production must use a real HTTPS domain.

Dependency note: the image still installs `social-auth-core[all]` from the
upstream NetBox requirements to preserve NetBox Docker compatibility. Reduce
that extra only after a clean image rebuild and Google login smoke test. Do not
remove `[all]` while validating unrelated SSO fixes.

To create the first admin user run this command:

```bash
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
```

If you need to restart Netbox from an empty database often,
you can also set the `SUPERUSER_*` variables in your `docker-compose.override.yml`.

[wiki-getting-started]: https://github.com/netbox-community/netbox-docker/wiki/Getting-Started

## Container Image Tags

New container images are built and published automatically every ~24h.

> We recommend to use either the `vX.Y.Z-a.b.c` tags or the `vX.Y-a.b.c` tags in production!

- `vX.Y.Z-a.b.c`, `vX.Y-a.b.c`:
  These are release builds containing _NetBox version_ `vX.Y.Z`.
  They contain the support files of _NetBox Docker version_ `a.b.c`.
  You must use _NetBox Docker version_ `a.b.c` to guarantee the compatibility.
  These images are automatically built from [the corresponding releases of NetBox][netbox-releases].
- `latest-a.b.c`:
  These are release builds, containing the latest stable version of NetBox.
  They contain the support files of _NetBox Docker version_ `a.b.c`.
  You must use _NetBox Docker version_ `a.b.c` to guarantee the compatibility.
- `snapshot-a.b.c`:
  These are prerelease builds.
  They contain the support files of _NetBox Docker version_ `a.b.c`.
  You must use _NetBox Docker version_ `a.b.c` to guarantee the compatibility.
  These images are automatically built from the [`main` branch of NetBox][netbox-main].

For each of the above tag, there is an extra tag:

- `vX.Y.Z`, `vX.Y`:
  This is the same version as `vX.Y.Z-a.b.c` (or `vX.Y-a.b.c`, respectively).
- `latest`
  This is the same version as `latest-a.b.c`.
  It always points to the latest version of _NetBox Docker_.
- `snapshot`
  This is the same version as `snapshot-a.b.c`.
  It always points to the latest version of _NetBox Docker_.

[netbox-releases]: https://github.com/netbox-community/netbox/releases
[netbox-main]: https://github.com/netbox-community/netbox/tree/main

## Documentation

Please refer [to our wiki on GitHub][netbox-docker-wiki] for further information on how to use the NetBox Docker image properly.
The wiki covers advanced topics such as using files for secrets, configuring TLS, deployment to Kubernetes, monitoring and configuring LDAP.

Our wiki is a community effort.
Feel free to correct errors, update outdated information or provide additional guides and insights.

[netbox-docker-wiki]: https://github.com/netbox-community/netbox-docker/wiki/

## Getting Help

Feel free to ask questions in our [GitHub Community][netbox-community]
or [join our Slack][netbox-docker-slack] and ask [in our channel `#netbox-docker`][netbox-docker-slack-channel],
which is free to use and where there are almost always people online that can help you.

If you need help with using NetBox or developing for it or against it's API
you may find [the `#netbox` channel][netbox-slack-channel] on the same Slack instance very helpful.

[netbox-community]: https://github.com/netbox-community/netbox-docker/discussions

## Dependencies

This project relies only on _Docker_ and _docker-compose_ meeting these requirements:

- The _Docker version_ must be at least `20.10.10`.
- The _containerd version_ must be at least `1.5.6`.
- The _docker-compose version_ must be at least `1.28.0`.

To check the version installed on your system run `docker --version` and `docker compose version`.

## Updating

Please read [the release notes][releases] carefully when updating to a new image version.
Note that the version of the NetBox Docker container image must stay in sync with the version of the Git repository.

If you update for the first time, be sure [to follow our _How To Update NetBox Docker_ guide in the wiki][netbox-docker-wiki-updating].

[releases]: https://github.com/netbox-community/netbox-docker/releases
[netbox-docker-wiki-updating]: https://github.com/netbox-community/netbox-docker/wiki/Updating

## Rebuilding the Image

`./build.sh` can be used to rebuild the container image.
See `./build.sh --help` for more information or `./build-latest.sh` for an example.

For more details on custom builds [consult our wiki][netbox-docker-wiki-build].

[netbox-docker-wiki-build]: https://github.com/netbox-community/netbox-docker/wiki/Build

## Tests

We have a test script.
It runs NetBox's own unit tests and ensures that NetBox starts:

```bash
IMAGE=docker.io/netboxcommunity/netbox:latest ./test.sh
```

## Support

This repository is currently maintained by the community.
The community is expected to help each other.

Please consider sponsoring the maintainers of this project.
