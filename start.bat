@echo off
REM Start script for Windows

echo Starting Video Download & S3 Upload Application...

REM Check if .env file exists
if not exist .env (
    echo Warning: .env file not found. Creating from env.example...
    if exist env.example (
        copy env.example .env
        echo Please edit .env file with your S3 credentials before continuing.
        pause
        exit /b 1
    ) else (
        echo Error: env.example not found. Please create .env file manually.
        pause
        exit /b 1
    )
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Create temp directory
if not exist tmp\jobs mkdir tmp\jobs

REM Start backend
echo Starting backend server...
cd backend
python main.py

pause


