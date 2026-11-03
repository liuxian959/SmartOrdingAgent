@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo    AiMenu Frontend - Dev Server
echo ========================================

echo [1/3] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install it from https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js detected.

echo [2/3] Checking dependencies...
if not exist "node_modules" (
    echo First run - installing dependencies...
    npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Check your network.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed.
) else (
    echo [OK] Dependencies already present.
)

echo [3/3] Starting dev server...
echo Frontend: http://localhost:3000  (backend must run at http://localhost:8000)
echo Press Ctrl+C to stop.
echo ========================================

npm run dev
pause
