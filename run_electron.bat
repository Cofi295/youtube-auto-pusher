@echo off
chcp 65001 > nul
taskkill /F /IM python.exe >nul 2>&1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0\electron-ui"
if not exist node_modules (
  npm install
  if errorlevel 1 pause & exit /b 1
)
npm start
pause
