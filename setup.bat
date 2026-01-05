@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo AI Assistant MVP - Setup (Windows BAT)
echo ============================================
echo.

rem Check python
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  echo Install Python 3.11+ and ensure "python" works in CMD.
  echo.
  exit /b 1
)

rem Create .env if missing
if not exist ".env" (
  if exist ".env.example" (
    copy /y ".env.example" ".env" >nul
    echo Created .env from .env.example
    echo IMPORTANT: Edit .env now (JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, OLLAMA_MODEL, APP_DOMAIN).
  ) else (
    echo [ERROR] .env.example not found.
    exit /b 1
  )
) else (
  echo .env already exists - not overwriting.
)

echo.

rem Create venv if missing
if not exist ".venv\Scripts\python.exe" (
  echo Creating venv in .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    exit /b 1
  )
) else (
  echo venv already exists.
)

echo.

rem Activate venv
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate venv.
  exit /b 1
)

echo Upgrading pip ...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip upgrade failed.
  exit /b 1
)

echo Installing requirements ...
pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  exit /b 1
)

echo.
echo ============================================
echo Setup done.
echo Next:
echo  1) Edit .env
echo  2) Start backend: run.bat
echo  3) (Optional) Start Caddy: caddy-run.bat
echo ============================================
echo.
pause
exit /b 0