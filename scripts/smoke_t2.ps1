param(
    [string]$Image = "agenthon-t2:dev",
    [string]$VerifierImage = "agenthon-t2-verifier:dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Upstream = Join-Path $ProjectRoot "upstream\track2-forecasting-public"
$UnitRelative = "units/t2-EXAMPLE-ust-curve-1m"
$RunId = "t2-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$RunDir = Join-Path $ProjectRoot "evidence\runs\$RunId"
$OutputDir = Join-Path $RunDir "output"
$LogPath = Join-Path $RunDir "smoke.log"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Materialize the exact pinned Git blobs so Windows autocrlf cannot invalidate
# the official unit manifest checksums.
$CanonicalRoot = Join-Path $RunDir "canonical"
$ArchivePath = Join-Path $RunDir "official-unit.tar"
New-Item -ItemType Directory -Path $CanonicalRoot -Force | Out-Null
git -c core.autocrlf=false -C $Upstream archive --format=tar --output=$ArchivePath HEAD $UnitRelative
if ($LASTEXITCODE -ne 0) { throw "Unable to archive pinned official unit" }
tar -xf $ArchivePath -C $CanonicalRoot
if ($LASTEXITCODE -ne 0) { throw "Unable to extract pinned official unit" }
$Unit = Join-Path $CanonicalRoot "units\t2-EXAMPLE-ust-curve-1m"

$ErrorActionPreference = "Continue"
docker run --rm --network=none --cpus=4 --memory=8g `
    --volume "${Unit}:/input:ro" `
    --volume "${OutputDir}:/output" `
    $Image forecast --panels /input/panels --text /input/text `
    --asof 2024-06-28 --out /output/forecast.parquet *> $LogPath
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) {
    Get-Content -LiteralPath $LogPath -Tail 80
    exit $Code
}

$ErrorActionPreference = "Continue"
docker buildx build --platform linux/amd64 --load `
    --file (Join-Path $ProjectRoot "packaging\t2-verifier\Dockerfile") `
    --tag $VerifierImage $ProjectRoot *> (Join-Path $RunDir "verifier-build.log")
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) {
    Get-Content -LiteralPath (Join-Path $RunDir "verifier-build.log") -Tail 80
    exit $Code
}

$ErrorActionPreference = "Continue"
docker run --rm `
    --volume "${Unit}:/unit:ro" `
    --volume "${OutputDir}:/out:ro" `
    $VerifierImage /unit /out --track forecasting >> $LogPath 2>&1
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content -LiteralPath $LogPath -Tail 80
if ($Code -eq 0) {
    Write-Output "SMOKE_OK run=$RunId output=$OutputDir"
}
exit $Code
