#Requires -Version 7
$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

# Load .env into process for APP_PORT display (Compose reads it itself).
$envFile = Join-Path (Get-Location) ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $name, $value = $_ -split "=", 2
        Set-Item -Path "Env:$name" -Value $value
    }
}

function Assert-Ok {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    # PowerShell can leave $LASTEXITCODE stale/$null after native commands.
    # Prefer $? and explicit container checks over raw LASTEXITCODE alone.
    if (-not $?) {
        throw $Message
    }
}

Write-Host "Building and starting Bar Vision..." -ForegroundColor Cyan

docker compose up --build -d
Assert-Ok "Docker Compose failed to start the stack."

Write-Host "Waiting for backend health..." -ForegroundColor Cyan

$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    $status = docker compose ps --status running --format "{{.Service}} {{.Status}}" 2>$null
    if ($status -match "backend .*healthy") {
        $healthy = $true
        break
    }

    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    docker compose logs backend --tail 80
    throw "Backend did not become healthy in time."
}

Write-Host "Running backend tests..." -ForegroundColor Cyan
docker compose exec -T backend pytest -q
Assert-Ok "Backend tests failed."

Write-Host ""
Write-Host "Bar Vision is up." -ForegroundColor Green
Write-Host "App:    http://localhost:$env:APP_PORT"
Write-Host "Health: http://localhost:$env:APP_PORT/api/v1/health"
