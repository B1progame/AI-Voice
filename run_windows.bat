@echo off
setlocal enabledelayedexpansion

REM ---- AI Assistant MVP (Stage 1) ----
REM 1) Create venv (if missing)
REM 2) Install deps
REM 3) Run uvicorn

cd /d %~dp0

if not exist .venv (
  echo Creating venv...
  python -m venv .venv
)

call .venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
pip install -r requirements.txt

echo Starting server...
echo Open: http://127.0.0.1:8000  (or via Caddy HTTPS as documented)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000