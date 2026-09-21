param(
    [string]$Image = "agenthon-t1:dev",
    [string]$SandboxImage = "finance-bench-sandbox:t1-pinned"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Upstream = Join-Path $ProjectRoot "upstream\track1-coding-public"
$UnitRelative = "units/t1-EXAMPLE-bs-greeks-pde"
$RunId = "t1-smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss")
$RunDir = Join-Path $ProjectRoot "evidence\runs\$RunId"
$OutputDir = Join-Path $RunDir "output"
$CanonicalRoot = Join-Path $RunDir "canonical"
$ArchivePath = Join-Path $RunDir "official-unit.tar"
$ProducerLog = Join-Path $RunDir "producer.log"
$SandboxLog = Join-Path $RunDir "sandbox-build.log"
$CheckerLog = Join-Path $RunDir "checker.log"
New-Item -ItemType Directory -Path $OutputDir,$CanonicalRoot -Force | Out-Null

git -c core.autocrlf=false -C $Upstream archive --format=tar --output=$ArchivePath HEAD $UnitRelative
if ($LASTEXITCODE -ne 0) { throw "Unable to archive pinned T1 exemplar" }
tar -xf $ArchivePath -C $CanonicalRoot
if ($LASTEXITCODE -ne 0) { throw "Unable to extract pinned T1 exemplar" }
$Unit = Join-Path $CanonicalRoot "units\t1-EXAMPLE-bs-greeks-pde"

$ErrorActionPreference = "Continue"
docker run --rm --network=none --cpus=4 --memory=8g `
    --volume "${Unit}:/input:ro" `
    --volume "${OutputDir}:/app/output" `
    --volume "${OutputDir}:/output" `
    $Image solve --task-dir /input --out /app/output *> $ProducerLog
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) { Get-Content -LiteralPath $ProducerLog -Tail 80; exit $Code }

$ErrorActionPreference = "Continue"
docker build --file (Join-Path $Upstream "docker\sandbox.Dockerfile") `
    --tag $SandboxImage $Upstream *> $SandboxLog
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) { Get-Content -LiteralPath $SandboxLog -Tail 80; exit $Code }

$ErrorActionPreference = "Continue"
docker run --rm --network=none `
    --env OUTPUT_DIR=/app/output `
    --env PYTHONDONTWRITEBYTECODE=1 `
    --volume "${Unit}:/input:ro" `
    --volume "${OutputDir}:/app/output" `
    --volume "${OutputDir}:/output" `
    $SandboxImage bash /input/checks/test.sh *> $CheckerLog
$Code = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($Code -ne 0) { Get-Content -LiteralPath $CheckerLog -Tail 80; exit $Code }

$Reward = Get-Content -LiteralPath (Join-Path $OutputDir "reward.json") | ConvertFrom-Json
$Report = Get-Content -LiteralPath (Join-Path $OutputDir "pytest_report.json") | ConvertFrom-Json
if ([double]$Reward.reward -ne 1.0 -or [int]$Report.summary.failed -ne 0) {
    Get-Content -LiteralPath $CheckerLog -Tail 80
    throw "T1 exemplar checker did not award reward=1.0"
}
Write-Output "SMOKE_OK run=$RunId reward=1.0 passed=$($Report.summary.passed) failed=$($Report.summary.failed)"
