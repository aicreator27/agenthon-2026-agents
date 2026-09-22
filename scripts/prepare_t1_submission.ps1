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
$Output = Join-Path $ProjectRoot "packaging\t1\submission.json"
$Descriptor = [ordered]@{
    schema_version = "1.1.0"
    interface_version = "2.0"
    competition_id = "agenthon2026-coding-$Phase"
    track = "coding"
    phase = $Phase
    category = "api"
    image = [ordered]@{
        registry = $Registry
        repository = $Repository
        digest = $Digest
    }
    image_access = $ImageAccess
    models = @(
        [ordered]@{
            name = "nvidia/nemotron-3-super-120b-a12b"
            version = "rl-030326-fp8"
            revision = "rl-030326-fp8"
            training_cutoff = "unpublished"
            access = "api"
        }
    )
    license = $LicenseId
    descriptor_digest = "sha256:" + ("0" * 64)
}
if ($TeamId) { $Descriptor.Insert(3, "team_id", $TeamId) }
$Json = $Descriptor | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($Output, $Json, (New-Object System.Text.UTF8Encoding $false))
Write-Output "WROTE_UNSEALED_DESCRIPTOR $Output"
if (-not $TeamId) { Write-Output "team_id omitted on purpose; qfbench2 submission pack derives it." }
Write-Output "Run qfbench2 submission pack --descriptor $Output --team-number <N> --out submission.zip"
