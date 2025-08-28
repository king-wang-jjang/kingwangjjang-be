Param(
  [Parameter(Position=0)]
  [string]$Command
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NETWORK_NAME = 'kingwangjjang-network'

function Test-CommandExists {
  param([string]$Name)
  try { Get-Command $Name -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

$script:UseComposeV2 = $false
function Initialize-Compose {
  try {
    docker compose version *> $null
    $script:UseComposeV2 = $true
  } catch {
    if (Test-CommandExists 'docker-compose') {
      $script:UseComposeV2 = $false
    } else {
      Write-Error '[ERROR] Docker Compose is not installed. Please install Docker Desktop or docker-compose.'
    }
  }
}

function Invoke-Compose {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
  if ($script:UseComposeV2) {
    & docker compose @Args
  } else {
    & docker-compose @Args
  }
}

function Ensure-Network {
  if (-not (docker network inspect $NETWORK_NAME *> $null)) {
    Write-Host "[INFO] Creating network: $NETWORK_NAME"
    docker network create $NETWORK_NAME | Out-Null
  }
}

function Ensure-LogsDir {
  New-Item -ItemType Directory -Force -Path 'logs' | Out-Null
}

function Ensure-EnvFile {
  if (-not (Test-Path '.env')) {
    if (Test-Path '.env.example') {
      Write-Host '[INFO] Copying .env.example to .env'
      Copy-Item '.env.example' '.env'
    } else {
      Write-Warning '[WARN] .env file not found. Create .env in root directory if needed.'
    }
  }
}

function Cmd-Up {
  Initialize-Compose
  Ensure-LogsDir
  Ensure-Network
  Ensure-EnvFile
  Invoke-Compose up -d
  Invoke-Compose ps
}

function Cmd-Down {
  Initialize-Compose
  Invoke-Compose down
}

function Cmd-Restart {
  Initialize-Compose
  Invoke-Compose down
  Cmd-Up
}

function Cmd-Logs {
  Initialize-Compose
  Invoke-Compose logs -f --tail=200
}

function Cmd-Ps {
  Initialize-Compose
  Invoke-Compose ps
}

function Cmd-Pull {
  Initialize-Compose
  Invoke-Compose pull
}

function Cmd-Clean {
  Initialize-Compose
  Invoke-Compose down -v --remove-orphans
}

function Show-Usage {
  @'
Usage: .\run.ps1 <command>

Commands:
  up        Start containers (background)
  down      Stop containers
  restart   Restart (down -> up)
  logs      Follow all logs
  ps        Show service status
  pull      Pull latest images
  clean     Clean all volumes/orphaned containers

Examples:
  powershell -ExecutionPolicy Bypass -File .\run.ps1 up
  .\run.ps1 logs
'@ | Write-Host
}

switch ($Command) {
  'up'       { Cmd-Up }
  'down'     { Cmd-Down }
  'restart'  { Cmd-Restart }
  'logs'     { Cmd-Logs }
  'ps'       { Cmd-Ps }
  'pull'     { Cmd-Pull }
  'clean'    { Cmd-Clean }
  { $_ -in @('', 'help', '-h', '--help') } { Show-Usage }
  default    { Write-Host "Unknown command: $Command`n"; Show-Usage; exit 1 }
}
