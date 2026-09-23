param(
    [switch]$Force
)

# Restore upstream/ at the exact pins recorded in sources/SOURCE_REGISTRY.md.
#
# upstream/ is deliberately NOT committed: the shared toolkit is CC BY-NC 4.0, so vendoring it
# into this repository would redistribute it under terms we do not hold. Cloning at a pinned
# commit gets the same bytes without that problem.
#
# Nothing in this project builds or runs until this has been done once: the verifier images
# COPY from upstream/, and every smoke, matrix and backtest reads the official units.
# Re-running is safe; a checkout already at its pin is left untouched.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$UpstreamRoot = Join-Path $ProjectRoot "upstream"

$Pins = @(
    @{ Name = "Agenthon2026-public";       Commit = "03fc89cc666354e999768381bb923e60be5c1cee";
       Url = "https://github.com/Agenthon-2026/Agenthon2026-public.git" },
    @{ Name = "track1-coding-public";      Commit = "25975fc743d67019827652b9dfbdefc712229533";
       Url = "https://github.com/Agenthon-2026/track1-coding-public.git" },
    @{ Name = "track2-forecasting-public"; Commit = "4ee40699e81f4ab50056c8835e67583035695692";
       Url = "https://github.com/Agenthon-2026/track2-forecasting-public.git" }
)

New-Item -ItemType Directory -Path $UpstreamRoot -Force | Out-Null
$Failed = @()

foreach ($Pin in $Pins) {
    $Dir = Join-Path $UpstreamRoot $Pin.Name
    $GitDir = Join-Path $Dir ".git"

    if ((Test-Path $GitDir) -and (-not $Force)) {
        $Head = (& git -c safe.directory=* -C $Dir rev-parse HEAD 2>$null)
        if ($Head -eq $Pin.Commit) {
            Write-Output ("OK      {0} already at pin" -f $Pin.Name)
            continue
        }
        Write-Output ("MOVING  {0} is at {1}" -f $Pin.Name, $Head.Substring(0, 12))
    }
    elseif (Test-Path $Dir) {
        if (-not $Force) { throw ("$Dir exists but is not a git checkout; rerun with -Force to replace it") }
        Remove-Item -Recurse -Force $Dir
    }

    if (-not (Test-Path $GitDir)) {
        Write-Output ("CLONE   {0}" -f $Pin.Name)
        & git clone --quiet $Pin.Url $Dir
        if ($LASTEXITCODE -ne 0) { $Failed += $Pin.Name; continue }
    }

    & git -c safe.directory=* -C $Dir fetch --quiet origin $Pin.Commit 2>$null
    & git -c safe.directory=* -C $Dir checkout --quiet --detach $Pin.Commit
    if ($LASTEXITCODE -ne 0) { $Failed += $Pin.Name; continue }

    # Verify rather than trust: a wrong pin silently changes what every gate is measured against.
    $Head = (& git -c safe.directory=* -C $Dir rev-parse HEAD)
    if ($Head -ne $Pin.Commit) {
        Write-Output ("MISMATCH {0}: HEAD {1} != pin {2}" -f $Pin.Name, $Head, $Pin.Commit)
        $Failed += $Pin.Name
        continue
    }
    Write-Output ("PINNED  {0} @ {1}" -f $Pin.Name, $Pin.Commit.Substring(0, 12))
}

if ($Failed.Count -gt 0) {
    throw ("Failed to pin: {0}" -f ($Failed -join ", "))
}
Write-Output "BOOTSTRAP_OK all upstream pins match sources/SOURCE_REGISTRY.md"
