param(
    [string]$TeamId,
    [Parameter(Mandatory = $true)][string]$Repository,
    [Parameter(Mandatory = $true)][string]$Digest,
    [string]$LicenseId = "MIT",
    [ValidateSet("dev", "final")][string]$Phase = "dev",
    [string]$Registry = "ghcr.io",
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
# qfbench2_common.team_claim.seal_for_team refuses a descriptor whose team_id disagrees with
# the id derived from the team number and key -- its own message says to remove the field. So
# team_id is omitted unless the caller passes the already-derived value, and `pack` fills it in.
$Descriptor = [ordered]@{
    schema_version = "1.1.0"
    interface_version = "2.0"
    competition_id = "agenthon2026-forecasting-$Phase"
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
if ($TeamId) { $Descriptor.Insert(3, "team_id", $TeamId) }
# Windows PowerShell 5.1 writes a BOM for -Encoding utf8, and the official toolkit reads the
# descriptor with json.load, which rejects a BOM outright ("Unexpected UTF-8 BOM"). Write the
# bytes ourselves so `qfbench2 submission pack` can actually read what we produce.
$Json = $Descriptor | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($Output, $Json, (New-Object System.Text.UTF8Encoding $false))
Write-Output "WROTE_UNSEALED_DESCRIPTOR $Output"
if (-not $TeamId) { Write-Output "team_id omitted on purpose; qfbench2 submission pack derives it." }
Write-Output "Run qfbench2 submission pack --descriptor $Output --team-number <N> --out submission.zip"

