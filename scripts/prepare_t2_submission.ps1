param(
    [Parameter(Mandatory = $true)][string]$TeamId,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Digest,
    [Parameter(Mandatory = $true)][string]$LicenseId,
    [ValidateSet("dev", "final")][string]$Phase = "dev",
    [string]$Registry = "docker.io",
    [ValidateSet("public", "organizer_mirror")][string]$ImageAccess = "public"
)

$ErrorActionPreference = "Stop"
if ($Digest -notmatch '^sha256:[0-9a-f]{64}$') {
    throw "Digest must be lowercase sha256:<64 hex>"
}
if ($Repository -notmatch '^[a-z0-9]+([._-][a-z0-9]+)*(/[a-z0-9]+([._-][a-z0-9]+)*)*$') {
    throw "Repository does not match the official lowercase descriptor pattern"
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Output = Join-Path $ProjectRoot "packaging\t2\submission.json"
$Descriptor = [ordered]@{
    schema_version = "1.1.0"
    interface_version = "2.0"
    competition_id = "agenthon2026-forecasting-$Phase"
    team_id = $TeamId
    track = "forecasting"
    phase = $Phase
    category = "api"
    image = [ordered]@{
        registry = $Registry
        repository = $Repository
        digest = $Digest
    }
    image_access = $ImageAccess
    models = @()
    license = $LicenseId
    descriptor_digest = "sha256:" + ("0" * 64)
}
$Descriptor | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding utf8
Write-Output "WROTE_UNSEALED_DESCRIPTOR $Output"
Write-Output "Run qfbench2 submission pack; it verifies team_id and seals descriptor_digest."

