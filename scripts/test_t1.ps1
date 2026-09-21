param(
    [string]$Image = "agenthon-t1:dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogPath = Join-Path $ProjectRoot "evidence\reports\test-t1.log"

$ErrorActionPreference = "Continue"
docker run --rm `
    --volume "${ProjectRoot}:/workspace:ro" `
    --workdir /workspace `
    --env "PYTHONPATH=/workspace/core/src:/workspace/tracks/t1_agenthon/src" `
    $Image python3 -m unittest discover -s /workspace/tests/contracts -p "test_t1_submission.py" `
    *> $LogPath
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content -LiteralPath $LogPath -Tail 80
exit $Code
