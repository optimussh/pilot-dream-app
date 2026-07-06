# Docker Hub 연결 불안정 시 베이스 이미지를 먼저 받은 뒤 빌드합니다.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$image = "python:3.11-slim-bookworm"
$env:DOCKER_BUILDKIT = "0"
$env:COMPOSE_DOCKER_CLI_BUILD = "0"
$maxRetries = 5

Write-Host "=== 1/2 베이스 이미지 다운로드: $image ===" -ForegroundColor Cyan
for ($i = 1; $i -le $maxRetries; $i++) {
    Write-Host "시도 $i / $maxRetries ..."
    docker pull $image
    if ($LASTEXITCODE -eq 0) {
        Write-Host "다운로드 성공!" -ForegroundColor Green
        break
    }
    if ($i -eq $maxRetries) {
        Write-Host "실패: Docker Hub 연결을 확인하세요." -ForegroundColor Red
        Write-Host "  - Docker Desktop 재시작"
        Write-Host "  - VPN 끄기"
        Write-Host "  - Settings > Docker Engine > registry-mirrors 설정"
        exit 1
    }
    Start-Sleep -Seconds 8
}

Write-Host "`n=== 2/2 앱 빌드 & 실행 ===" -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n완료! http://localhost:5000" -ForegroundColor Green
docker compose ps