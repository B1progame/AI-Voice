# Runs the FastAPI backend on Windows with env loaded from .env
# Usage:
#   ./run.ps1
# Notes:
# - Make sure you activated the venv first (see README).

$ErrorActionPreference = "Stop"

# Load .env into process env
$envPath = Join-Path $PSScriptRoot ".env"
if (!(Test-Path $envPath)) {
  Write-Host "No .env found. Copy .env.example to .env and edit it."
  exit 1
}

Get-Content $envPath | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) { return }
  $kv = $line.Split("=", 2)
  if ($kv.Count -ne 2) { return }
  $key = $kv[0].Trim()
  $val = $kv[1].Trim()
  [System.Environment]::SetEnvironmentVariable($key, $val, "Process")
}

$host = $env:APP_HOST
$port = $env:APP_PORT
if ([string]::IsNullOrWhiteSpace($host)) { $host = "127.0.0.1" }
if ([string]::IsNullOrWhiteSpace($port)) { $port = "8000" }

Write-Host "Starting backend on http://$host`:$port"
python -m uvicorn backend.app.main:app --host $host --port $port