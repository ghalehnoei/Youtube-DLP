@echo off
REM Stop both backend and frontend servers

echo Stopping Backend and Frontend servers...
echo.

REM Find and kill backend process on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Stopping Backend (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo Backend process not found or already stopped.
    ) else (
        echo Backend stopped successfully.
    )
)

REM Find and kill frontend process on port 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Stopping Frontend (PID %%a)...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo Frontend process not found or already stopped.
    ) else (
        echo Frontend stopped successfully.
    )
)

echo.
echo Done! Both servers have been stopped.
pause

