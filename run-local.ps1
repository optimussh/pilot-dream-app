# Docker 없이 로컬 실행 (Docker 실패 시 대안)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
Write-Host "http://127.0.0.1:5000" -ForegroundColor Green
python -m flask run --host=0.0.0.0 --port=5000