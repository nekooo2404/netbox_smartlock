$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $PSScriptRoot
$NetBoxEnvPath = Join-Path $ProjectDir "env\netbox.env"

function Import-DotEnvIfMissing {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($Line in Get-Content $Path) {
        $TrimmedLine = $Line.Trim()
        if (-not $TrimmedLine -or $TrimmedLine.StartsWith("#")) {
            continue
        }

        $Parts = $TrimmedLine -split "=", 2
        if ($Parts.Count -ne 2 -or $Parts[0] -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
            continue
        }

        $Name = $Parts[0]
        if ([Environment]::GetEnvironmentVariable($Name, "Process")) {
            continue
        }

        [Environment]::SetEnvironmentVariable($Name, $Parts[1].Trim(), "Process")
    }
}

Import-DotEnvIfMissing -Path $NetBoxEnvPath

$KeycloakBaseUrl = [Environment]::GetEnvironmentVariable("KEYCLOAK_BASE_URL", "Process")
if (-not $KeycloakBaseUrl) {
    $KeycloakBaseUrl = "http://keycloak.localtest.me:8080"
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$Retries = 60,
        [int]$DelaySeconds = 2
    )

    for ($Attempt = 1; $Attempt -le $Retries; $Attempt++) {
        try {
            $Response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 500) {
                return
            }
        } catch {
            if ($Attempt -eq $Retries) {
                throw
            }
        }

        Start-Sleep -Seconds $DelaySeconds
    }
}

$ComposeFiles = @(
    "-f", "docker-compose.yml",
    "-f", "docker-compose.override.yml",
    "-f", "docker-compose.keycloak.yml"
)

docker compose @ComposeFiles up -d ldap keycloak | Out-Null
Wait-HttpReady -Url "$KeycloakBaseUrl/realms/master"
python ".\keycloak\configure_ldap_oidc.py"
