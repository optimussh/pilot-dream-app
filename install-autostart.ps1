# Register a logon scheduled task so the app comes back after reboot.
# Requires Docker Desktop "Start when you log in" (usually already on).
#
# Run once (normal user is fine):
#   powershell -ExecutionPolicy Bypass -File .\install-autostart.ps1
#
# Uninstall:
#   Unregister-ScheduledTask -TaskName "PilotDreamApp-EnsureRunning" -Confirm:$false

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$TaskName = "PilotDreamApp-EnsureRunning"
$ScriptPath = Join-Path $PSScriptRoot "ensure-running.ps1"

if (-not (Test-Path $ScriptPath)) {
    throw "Missing: $ScriptPath"
}

# Remove previous registration if present
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false

$arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $PSScriptRoot

# Delay so Google Drive / Docker Desktop can start first
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT1M"  # 1 minute after logon

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Start Pilot Dream Docker stack after logon (web :5000, sim :5001)" |
    Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Script : $ScriptPath"
Write-Host "  When   : 1 minute after user logon"
Write-Host "  Log    : $env:LOCALAPPDATA\pilot-dream-app\ensure-running.log"
Write-Host ""
Write-Host "Also confirm Docker Desktop: Settings > General > Start Docker Desktop when you sign in"
Write-Host "Test now:  .\ensure-running.ps1"
Write-Host "Uninstall: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
