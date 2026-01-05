@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ===============================
rem Load .env
rem ===============================
set "ENV_FILE=%~dp0.env"
if not exist "%ENV_FILE%" (
  echo [ERROR] No .env found. Create it first.
  exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
  set "KEY=%%A"
  set "VAL=%%B"
  for /f "tokens=* delims= " %%K in ("!KEY!") do set "KEY=%%K"
  if not "!KEY!"=="" (
    if not "!KEY:~0,1!"=="#" (
      if "!VAL:~0,1!"=="^"" (
        if "!VAL:~-1!"=="^"" (
          set "VAL=!VAL:~1,-1!"
        )
      )
      set "!KEY!=!VAL!"
    )
  )
)

if "%APP_DOMAIN%"=="" (
  echo [ERROR] APP_DOMAIN is not set in .env
  echo Example: APP_DOMAIN=192.168.178.20
  exit /b 1
)

if "%APP_PORT%"=="" set "APP_PORT=8000"

echo Starting Caddy for domain: %APP_DOMAIN%
echo Proxy -> 127.0.0.1:%APP_PORT%
echo.

rem Start Caddy
caddy version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Caddy not found in PATH.
  echo Install it (e.g. scoop install caddy) and ensure "caddy" works in CMD.
  exit /b 1
)

caddy run --config "%~dp0Caddyfile"
exit /b %ERRORLEVEL%