param(
    [string]$Image = "agenthon-t2:dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "evidence\reports"
$LogPath = Join-Path $LogDir "test-t2.log"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Discovery is scoped to test_t2_*.py on purpose. This runs inside the T2 submission image,
# which by design bakes only core/ and tracks/t2_agenthon/ (see packaging/t2/Dockerfile), so
# T1 contract tests in the same directory cannot import their module here. They are not broken;
# they belong to the T1 image.
$ErrorActionPreference = "Continue"
docker run --rm `
    --volume "${ProjectRoot}:/workspace:ro" `
    --workdir /workspace `
    --env "PYTHONPATH=/workspace/core/src:/workspace/tracks/t2_agenthon/src" `
    $Image python3 -m unittest discover -s /workspace/tests/contracts -p "test_t2_*.py" `
    *> $LogPath
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content -LiteralPath $LogPath -Tail 80
exit $Code
