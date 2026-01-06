@echo off
setlocal enabledelayedexpansion

REM ---- AI Assistant MVP (Stage 1) ----

REM 1. Ensure the script runs from the folder where this file is saved
cd /d "%~dp0"

echo Starting Caddy...
caddy run --config .\Caddyfile --adapter caddyfile

REM 2. Keep window open if Caddy crashes so you can read the error
pause