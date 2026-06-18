$ErrorActionPreference = "Stop"

$ComposeFiles = @(
    "-f", "docker-compose.yml",
    "-f", "docker-compose.override.yml",
    "-f", "docker-compose.keycloak.yml"
)

docker compose @ComposeFiles up -d ldap keycloak | Out-Null
python ".\keycloak\configure_ldap_oidc.py"
