@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate.bat
if not exist venv\.deps_installed (
  python -m pip install -r requirements.txt
  if errorlevel 1 pause & exit /b 1
  echo ok>venv\.deps_installed
)
echo [YouTube Auto Pusher] Starting...
python main.py
pause
