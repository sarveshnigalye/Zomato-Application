# AI-Powered Restaurant Recommendation System — Launch Script
# Starts both FastAPI Backend (port 8000) and Frontend Server (port 3000)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Launching AI Restaurant Recommendation System" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# 1. Start FastAPI Backend in a separate process window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host '--- FastAPI Backend (Port 8000) ---' -ForegroundColor Green; & '.\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

# 2. Start Frontend HTTP Server in a separate process window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$ProjectRoot'; Write-Host '--- Frontend Server (Port 3000) ---' -ForegroundColor Yellow; & '.\.venv\Scripts\python.exe' -m http.server 3000 --directory frontend"

Write-Host "`n[OK] Both servers launched in dedicated terminal windows!" -ForegroundColor Green
Write-Host "  - Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "  - Swagger Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Frontend UI:  http://localhost:3000" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Cyan
