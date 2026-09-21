param(
    [string]$Image = "agenthon-t2:dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "evidence\reports"
$LogPath = Join-Path $LogDir "build-t2.log"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$ErrorActionPreference = "Continue"
docker buildx build --platform linux/amd64 --load `
    --file (Join-Path $ProjectRoot "packaging\t2\Dockerfile") `
    --tag $Image $ProjectRoot *> $LogPath
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) {
    Get-Content -LiteralPath $LogPath -Tail 80
    exit $Code
}

$Inspection = docker image inspect $Image | ConvertFrom-Json
$InspectCode = $LASTEXITCODE
$Label = $Inspection[0].Config.Labels.'qfbench2.interface_version'
if ($InspectCode -ne 0 -or $Label -ne "2.0") {
    throw "Image interface label is missing or incorrect: $Label"
}

$ErrorActionPreference = "Continue"
docker run --rm $Image forecast --help | Out-Null
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) {
    throw "forecast --help failed"
}

Write-Output "BUILD_OK image=$Image interface=2.0 log=$LogPath"
