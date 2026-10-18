@echo off
title AI Restaurant Recommendation System Launcher
echo ==========================================================
echo   Launching AI Restaurant Recommendation System
echo ==========================================================

cd /d "%~dp0"

echo Starting FastAPI Backend on port 8000...
start "Backend API (Port 8000)" powershell -NoExit -Command "Set-Location '%~dp0'; Write-Host '--- FastAPI Backend (Port 8000) ---' -ForegroundColor Green; & '.\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend Server on port 3000...
start "Frontend UI (Port 3000)" powershell -NoExit -Command "Set-Location '%~dp0'; Write-Host '--- Frontend Server (Port 3000) ---' -ForegroundColor Yellow; & '.\.venv\Scripts\python.exe' -m http.server 3000 --directory frontend"

echo.
echo [OK] Both servers launched in dedicated windows!
echo   - Backend API:  http://localhost:8000
echo   - Swagger Docs: http://localhost:8000/docs
echo   - Frontend UI:  http://localhost:3000
echo ==========================================================
pause
