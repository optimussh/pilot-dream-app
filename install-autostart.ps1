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
$SourceScript = Join-Path $PSScriptRoot "ensure-running.ps1"
$LocalDir = Join-Path $env:LOCALAPPDATA "pilot-dream-app"
$ScriptPath = Join-Path $LocalDir "ensure-running.ps1"

if (-not (Test-Path $SourceScript)) {
    throw "Missing: $SourceScript"
}
New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null
Copy-Item -LiteralPath $SourceScript -Destination $ScriptPath -Force

# Remove previous registration if present
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false

$arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $LocalDir

# One minute after logon, and every 5 minutes, so a dead port door
# is reopened without waiting for the next reboot.
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$atLogon.Delay = "PT1M"
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 9999)

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
    -Trigger @($atLogon, $repeat) `
    -Settings $settings `
    -Principal $principal `
    -Description "Start Pilot Dream Docker stack after logon (web :5000, sim :5001)" |
    Out-Null

Write-Host "Registered scheduled task: $TaskName" -ForegroundColor Green
Write-Host "  Script : $ScriptPath"
Write-Host "  When   : 1 minute after logon, then every 5 minutes"
Write-Host "  Log    : $env:LOCALAPPDATA\pilot-dream-app\ensure-running.log"
Write-Host ""
Write-Host "Also confirm Docker Desktop: Settings > General > Start Docker Desktop when you sign in"
Write-Host "Test now:  .\ensure-running.ps1"
Write-Host "Uninstall: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
