@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem ===============================
rem Load .env into environment
rem ===============================
set "ENV_FILE=%cd%\.env"

if not exist "%ENV_FILE%" (
  echo [ERROR] .env not found in: %cd%
  echo Please copy .env.example to .env and edit it.
  echo.
  pause
  exit /b 1
)

rem Read KEY=VALUE lines, ignore lines starting with #
for /f "usebackq eol=# tokens=1* delims==" %%A in ("%ENV_FILE%") do (
  if not "%%A"=="" (
    set "%%A=%%B"
  )
)

rem Defaults if not set
if not defined APP_HOST set "APP_HOST=127.0.0.1"
if not defined APP_PORT set "APP_PORT=8000"

echo ============================================
echo AI Assistant MVP - Backend Start
echo ============================================
echo Host: %APP_HOST%
echo Port: %APP_PORT%
echo DB:   backend\data\app.db
echo Log:  logs\app.log
echo ============================================
echo.

rem ===============================
rem Ensure venv exists
rem ===============================
if not exist "%cd%\.venv\Scripts\python.exe" (
  echo [ERROR] venv not found: .venv\Scripts\python.exe
  echo Run your setup steps first:
  echo   python -m venv .venv
  echo   call .\.venv\Scripts\activate.bat
  echo   python -m pip install --upgrade pip
  echo   pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)

rem Activate venv (MUST use call)
call "%cd%\.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate venv.
  echo.
  pause
  exit /b 1
)

rem Start uvicorn
python -m uvicorn backend.app.main:app --host %APP_HOST% --port %APP_PORT%
set "EXITCODE=%ERRORLEVEL%"

echo.
echo Backend exited with code %EXITCODE%
pause
exit /b %EXITCODE%