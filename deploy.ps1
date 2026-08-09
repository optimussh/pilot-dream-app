# Build image from this folder and start always-on containers (detached).
# Safe to re-run after reboot or after moving the project path.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$env:DOCKER_BUILDKIT = "1"
$ProjectName = "pilot-dream-app"

function Test-DockerReady {
    try {
        docker info 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

Write-Host "=== Pilot Dream deploy ===" -ForegroundColor Cyan
Write-Host "Project: $PSScriptRoot"

if (-not (Test-DockerReady)) {
    Write-Host "Docker engine not ready. Starting Docker Desktop..." -ForegroundColor Yellow
    $dd = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) {
        Start-Process $dd
    } else {
        Write-Host "Docker Desktop not found at: $dd" -ForegroundColor Red
        exit 1
    }
    $deadline = (Get-Date).AddMinutes(3)
    while (-not (Test-DockerReady)) {
        if ((Get-Date) -gt $deadline) {
            Write-Host "Timed out waiting for Docker. Open Docker Desktop and retry." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 3
        Write-Host "  waiting for Docker..."
    }
}

# Drop legacy containers that may still bind the old C:\Users\...\ path
Write-Host "`n=== Stop previous stack (if any) ===" -ForegroundColor Cyan
# Docker may write warnings to stderr; do not treat that as terminating error
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose -p $ProjectName down --remove-orphans 2>&1 | Out-Null
docker rm -f pilot-dream-web pilot-dream-sim pilot-dream-app-web-1 pilot-dream-app-sim-1 2>&1 | Out-Null
$ErrorActionPreference = $prevEap

Write-Host "`n=== Build & start (always-on) ===" -ForegroundColor Cyan
$ErrorActionPreference = "Continue"
docker compose -p $ProjectName up -d --build
$upCode = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($upCode -ne 0) {
    Write-Host "compose up failed." -ForegroundColor Red
    exit $upCode
}

Write-Host "`n=== Status ===" -ForegroundColor Cyan
docker compose -p $ProjectName ps

Write-Host "`nWaiting for web health..." -ForegroundColor Cyan
$ok = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
            $ok = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ok) {
    Write-Host "`nOK  Main app:  http://127.0.0.1:5000" -ForegroundColor Green
    Write-Host "OK  Simulator: http://127.0.0.1:5001" -ForegroundColor Green
    Write-Host "Containers use restart: unless-stopped (survive reboot if Docker Desktop starts)." -ForegroundColor Green
} else {
    Write-Host "`nContainers started but health check not ready yet." -ForegroundColor Yellow
    Write-Host "Check: docker compose -p $ProjectName logs --tail 50"
    Write-Host "Open:  http://127.0.0.1:5000"
    exit 1
}
