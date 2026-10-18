# After logon, and again every few minutes: make http://127.0.0.1:5000 answer.
# Does not rebuild. Uses the containers Docker already has, so it still works
# when Google Drive is slow to mount.
$ErrorActionPreference = "Continue"

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

function Test-WebUp {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing -TimeoutSec 8
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500 -and $r.RawContentLength -gt 200)
    } catch {
        return $false
    }
}

function Repair-Port5000 {
    Write-Log "port 5000 did not answer — resetting the Windows port door"
    docker stop pilot-dream-web 2>$null | Out-Null
    Start-Sleep -Seconds 2
    $owners = @(Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($procId in $owners) {
        if (-not $procId) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue
        if ($proc -and $proc.Name -eq "wslrelay.exe") {
            Write-Log "stopping stale wslrelay $procId"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
    docker start pilot-dream-web 2>$null | Out-Null
}

Write-Log "ensure-running start"

if (-not (Test-DockerReady)) {
    Write-Log "Docker not ready — launching Docker Desktop"
    $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
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

docker start pilot-dream-web pilot-dream-sim 2>$null | Out-Null
$running = docker ps --filter "name=pilot-dream-web" --filter "status=running" -q
if (-not $running) {
    Write-Log "container missing — compose up needs the project folder"
    $project = "G:\내 드라이브\10_개발\Projects\pilot-dream-app"
    if (Test-Path (Join-Path $project "docker-compose.yml")) {
        Push-Location $project
        docker compose -p pilot-dream-app up -d
        $upCode = $LASTEXITCODE
        Pop-Location
        if ($upCode -ne 0) {
            Write-Log "compose up failed (exit $upCode)"
            exit $upCode
        }
    } else {
        Write-Log "FAIL: project folder not available yet"
        exit 1
    }
}

if (Test-WebUp) {
    Write-Log "OK http://127.0.0.1:5000"
    exit 0
}

Repair-Port5000
for ($i = 1; $i -le 15; $i++) {
    if (Test-WebUp) {
        Write-Log "OK http://127.0.0.1:5000 after port repair"
        exit 0
    }
    Start-Sleep -Seconds 2
}

Write-Log "FAIL: http://127.0.0.1:5000 still not answering"
exit 1
