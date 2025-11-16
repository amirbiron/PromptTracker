@echo off
REM Script for running PromptTracker Bot on Windows

echo Starting PromptTracker Bot...
echo.

REM Check for .env file
if not exist .env (
    echo .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo Please edit .env file with your credentials
    pause
    exit /b 1
)

REM Create virtual environment if needed
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Run the bot
echo.
echo Starting bot...
echo Press Ctrl+C to stop
echo.
python bot.py

pause
