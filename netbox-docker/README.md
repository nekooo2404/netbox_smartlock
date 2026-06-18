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

## Local Keycloak SSO

This repository includes `docker-compose.keycloak.yml` for local Keycloak SSO.
The local architecture is LDAP -> Keycloak -> OIDC -> NetBox. NetBox does not connect to LDAP directly.

It imports realm `netbox-dev`, client `netbox-dev`, roles `dcim-admin`/`dcim-guest`,
Keycloak groups `Admin`/`Guest`, and starts an internal LDAP service with demo users
`ldap-admin` and `ldap-guest`. LDAP is the identity source for internal app users;
NetBox does not connect to LDAP directly.

Run NetBox with Keycloak:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml up -d --build
```

Apply LDAP federation, role/group mappers, and trigger LDAP sync:

```powershell
powershell -ExecutionPolicy Bypass -File .\keycloak\configure-ldap-oidc.ps1
```

Bootstrap NetBox RBAC for the synced `Admin`/`Guest` groups:

```powershell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.keycloak.yml exec netbox /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py smartlock_bootstrap_rbac
```

OpenID discovery:

```text
http://keycloak.local:8080/realms/netbox-dev/.well-known/openid-configuration
```

Credentials:

```text
Keycloak admin: admin / admin
LDAP admin SSO user: ldap-admin / admin
LDAP guest SSO user: ldap-guest / guest
```

The imported Keycloak client exposes `groups` and `roles` OIDC claims. NetBox runs the custom
`netbox_smartlock.auth_pipeline.sync_keycloak_groups` social-auth pipeline step and
syncs allow-listed Keycloak groups/roles into NetBox groups on each login:

```env
KEYCLOAK_GROUP_SYNC_ENABLED=True
KEYCLOAK_GROUP_SYNC_GROUPS=Admin Guest
KEYCLOAK_GROUP_SYNC_REMOVE=True
KEYCLOAK_GROUP_SYNC_GROUP_MAP=dcim-admin=Admin dcim-guest=Guest
KEYCLOAK_GROUP_SYNC_ROLE_MAP=dcim-admin=Admin dcim-guest=Guest
```

Only the allow-listed groups are managed by the pipeline. Existing local NetBox
groups outside that list are left untouched.

The SmartLock plugin API accepts Keycloak Bearer JWTs on `/api/plugins/smartlock/...`.
Tokens must be issued by realm `netbox-dev` for client `netbox-dev`.

Region/Site scope remains enforced by NetBox ObjectPermission constraints. Use
`smartlock_bootstrap_rbac` for the default local setup, then tighten Region/Site
constraints in NetBox for customer- or tenant-specific access.

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
