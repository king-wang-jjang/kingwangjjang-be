Param(
  [Parameter(Position=0)]
  [string]$Command
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $RootDir 'logs\dev'
$PidFile = Join-Path $RootDir '.dev-pids'

# Kept as a literal for testability and for grep-friendly operational checks.
$DevEnv = 'SERVER_RUN_MODE=FALSE AUTH_COOKIE_SECURE=FALSE'

$Services = @(
  @{ Name = 'api-gateway'; Port = 8000 },
  @{ Name = 'board-service'; Port = 33333 },
  @{ Name = 'user-service'; Port = 33334 },
  @{ Name = 'comment-service'; Port = 33335 }
)

function Ensure-Dirs {
  New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

function Ensure-Env {
  if (-not (Test-Path (Join-Path $RootDir '.env'))) {
    Write-Warning ".env not found under $RootDir. Services may fail to start."
  }
}

function Test-ProcessRunning {
  param([int]$PidValue)
  try {
    Get-Process -Id $PidValue -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  }
}

function Start-DevService {
  param(
    [string]$Name,
    [int]$Port
  )

  $serviceDir = Join-Path $RootDir $Name
  $logFile = Join-Path $LogDir "$Name.log"

  if (-not (Test-Path $serviceDir)) {
    throw "service directory not found: $serviceDir"
  }

  $command = "`$env:SERVER_RUN_MODE='FALSE'; `$env:AUTH_COOKIE_SECURE='FALSE'; poetry run uvicorn app.main:app --host 0.0.0.0 --port $Port *> '$logFile'"
  $process = Start-Process `
    -FilePath 'powershell' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $command) `
    -WorkingDirectory $serviceDir `
    -WindowStyle Hidden `
    -PassThru

  "$Name $($process.Id) $Port $logFile" | Add-Content -Encoding UTF8 -Path $PidFile
  Write-Host "[INFO] started $Name on :$Port pid=$($process.Id) log=$logFile"
}

function Cmd-Up {
  Ensure-Dirs
  Ensure-Env
  Cmd-Down | Out-Null
  Set-Content -Encoding UTF8 -Path $PidFile -Value ''

  foreach ($service in $Services) {
    Start-DevService -Name $service.Name -Port $service.Port
  }

  Cmd-Ps
}

function Cmd-Down {
  if (-not (Test-Path $PidFile)) {
    return
  }

  Get-Content $PidFile | Where-Object { $_.Trim() -ne '' } | ForEach-Object {
    $parts = $_ -split ' ', 4
    $name = $parts[0]
    $pidValue = [int]$parts[1]

    if (Test-ProcessRunning -PidValue $pidValue) {
      Stop-Process -Id $pidValue -Force
      Write-Host "[INFO] stopped $name pid=$pidValue"
    }
  }

  Remove-Item -Force $PidFile
}

function Cmd-Restart {
  Cmd-Down
  Cmd-Up
}

function Cmd-Logs {
  Ensure-Dirs
  Get-Content -Wait -Tail 100 (Join-Path $LogDir '*.log')
}

function Cmd-Ps {
  if (-not (Test-Path $PidFile)) {
    Write-Host '[INFO] no dev services tracked'
    return
  }

  Get-Content $PidFile | Where-Object { $_.Trim() -ne '' } | ForEach-Object {
    $parts = $_ -split ' ', 4
    $name = $parts[0]
    $pidValue = [int]$parts[1]
    $port = $parts[2]
    $logFile = $parts[3]
    $status = if (Test-ProcessRunning -PidValue $pidValue) { 'running' } else { 'stopped' }
    Write-Host "$name pid=$pidValue port=$port status=$status log=$logFile"
  }
}

function Show-Usage {
  @'
Usage: .\dev.ps1 <command>

Commands:
  up        Start local source services in the background
  down      Stop local source services
  restart   Restart local source services
  logs      Follow local service logs
  ps        Show local service process status

Examples:
  powershell -ExecutionPolicy Bypass -File .\dev.ps1 up
  .\dev.ps1 logs
'@ | Write-Host
}

switch ($Command) {
  'up'       { Cmd-Up }
  'down'     { Cmd-Down }
  'restart'  { Cmd-Restart }
  'logs'     { Cmd-Logs }
  'ps'       { Cmd-Ps }
  { $_ -in @('', 'help', '-h', '--help') } { Show-Usage }
  default    { Write-Host "Unknown command: $Command`n"; Show-Usage; exit 1 }
}
