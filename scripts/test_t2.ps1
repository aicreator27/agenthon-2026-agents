param(
    [string]$Image = "agenthon-t2:dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "evidence\reports"
$LogPath = Join-Path $LogDir "test-t2.log"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$ErrorActionPreference = "Continue"
docker run --rm `
    --volume "${ProjectRoot}:/workspace:ro" `
    --workdir /workspace `
    --env "PYTHONPATH=/workspace/core/src:/workspace/tracks/t2_agenthon/src" `
    $Image python3 -m unittest discover -s /workspace/tests/contracts -p "test_*.py" `
    *> $LogPath
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content -LiteralPath $LogPath -Tail 80
exit $Code
