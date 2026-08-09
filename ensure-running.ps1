# Lightweight reboot helper: ensure stack is up without full rebuild.
# Used by Windows Task Scheduler after logon (see install-autostart.ps1).
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$ProjectName = "pilot-dream-app"
$LogDir = Join-Path $env:LOCALAPPDATA "pilot-dream-app"
$LogFile = Join-Path $LogDir "ensure-running.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log([string]$msg) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Test-DockerReady {
    try {
        docker info 1>$null 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

Write-Log "ensure-running start (cwd=$PSScriptRoot)"

if (-not (Test-DockerReady)) {
    Write-Log "Docker not ready — launching Docker Desktop"
    $dd = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) { Start-Process $dd }
    $deadline = (Get-Date).AddMinutes(5)
    while (-not (Test-DockerReady)) {
        if ((Get-Date) -gt $deadline) {
            Write-Log "FAIL: Docker did not become ready"
            exit 1
        }
        Start-Sleep -Seconds 5
    }
    Write-Log "Docker ready"
}

# If image missing, full deploy (needs project files online)
$img = docker images -q pilot-dream-app-web:latest
if (-not $img) {
    Write-Log "Image missing — running deploy.ps1"
    & (Join-Path $PSScriptRoot "deploy.ps1")
    exit $LASTEXITCODE
}

# Prefer start of existing compose project; fall back to up -d
docker compose -p $ProjectName start 2>$null
$running = docker ps --filter "name=pilot-dream-web" --filter "status=running" -q
if (-not $running) {
    Write-Log "Containers not running — docker compose up -d"
    docker compose -p $ProjectName up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Log "compose up failed (exit $LASTEXITCODE)"
        exit $LASTEXITCODE
    }
}

# Probe web
for ($i = 1; $i -le 20; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
            Write-Log "OK http://127.0.0.1:5000 status=$($r.StatusCode)"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 3
    }
}

Write-Log "WARN: stack started but web not responding yet"
exit 0
