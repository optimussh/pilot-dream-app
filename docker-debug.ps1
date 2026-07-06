# Docker 빌드/실행 전체 디버깅 — 결과를 docker-debug.log 에 저장
$LogFile = Join-Path $PSScriptRoot "docker-debug.log"
$ErrorActionPreference = "Continue"

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Set-Location $PSScriptRoot
"" | Set-Content -Path $LogFile -Encoding UTF8
Log "=== Pilot Dream Docker Debug ==="
Log "PWD: $(Get-Location)"

# 0. Docker 데몬 확인
Log "--- docker version ---"
docker version 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) {
    Log "FAIL: Docker Desktop이 실행 중인지 확인하세요."
    exit 1
}

Log "--- docker compose version ---"
docker compose version 2>&1 | ForEach-Object { Log $_ }

# 1. 포트 5000 사용 여부
Log "--- port 5000 check ---"
$port = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($port) { Log "WARN: 포트 5000 사용 중 — 기존 프로세스 종료 필요할 수 있음" }
else { Log "OK: 포트 5000 비어 있음" }

# 2. 베이스 이미지 pull (재시도)
$image = "python:3.11-slim-bookworm"
$pulled = $false
for ($i = 1; $i -le 5; $i++) {
    Log "--- docker pull $image (시도 $i/5) ---"
    docker pull $image 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -eq 0) { $pulled = $true; break }
    Log "pull 실패, 10초 대기..."
    Start-Sleep -Seconds 10
}
if (-not $pulled) {
    Log "FAIL: 베이스 이미지 다운로드 실패"
    Log "해결: Docker Desktop 재시작, VPN 끄기, Settings>Docker Engine 에 registry-mirrors 추가:"
    Log '  "registry-mirrors": ["https://docker.m.daocloud.io"]'
    exit 1
}

# 3. BuildKit 끄고 빌드 (grpc 오류 회피)
$env:DOCKER_BUILDKIT = "0"
$env:COMPOSE_DOCKER_CLI_BUILD = "0"

Log "--- docker compose build ---"
docker compose build --progress=plain 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) {
    Log "FAIL: docker compose build 실패"
    exit 1
}

Log "--- docker compose up -d ---"
docker compose up -d 2>&1 | ForEach-Object { Log $_ }
if ($LASTEXITCODE -ne 0) {
    Log "FAIL: docker compose up 실패"
    exit 1
}

Start-Sleep -Seconds 5

Log "--- docker compose ps ---"
docker compose ps 2>&1 | ForEach-Object { Log $_ }

Log "--- docker compose logs web (last 40) ---"
docker compose logs web --tail 40 2>&1 | ForEach-Object { Log $_ }

# 4. HTTP 헬스체크
Log "--- HTTP check localhost:5000 ---"
try {
    $r = Invoke-WebRequest -Uri "http://localhost:5000/" -UseBasicParsing -TimeoutSec 15
    Log "OK: HTTP $($r.StatusCode)"
} catch {
    Log "FAIL: HTTP 접속 실패 — $($_.Exception.Message)"
    Log "컨테이너 로그를 확인하세요."
    exit 1
}

Log "=== SUCCESS: http://localhost:5000 ==="
exit 0