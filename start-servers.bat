@echo off
REM Start both backend and frontend servers in separate windows

echo Starting Backend and Frontend servers...
echo.

REM Start backend in a new window
start "Backend Server" cmd /k "cd /d %~dp0backend && ..\venv\Scripts\activate.bat && python main.py"

REM Wait a moment for backend to start
timeout /t 2 /nobreak >nul

REM Start frontend in a new window
start "Frontend Server" cmd /k "cd /d %~dp0frontend && npm start"

echo.
echo Both servers are starting in separate windows.
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this window (servers will continue running)...
pause >nul

