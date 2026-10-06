@echo off
REM CultureLens Setup Script for Windows
REM Creates a virtual environment, installs dependencies, and downloads the spaCy model.

echo ============================================
echo   CultureLens - Setup Script (Windows)
echo ============================================
echo.

REM Create virtual environment
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment. Make sure Python 3.10+ is installed.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Virtual environment already exists, skipping creation.
)

REM Activate and install requirements
echo [2/4] Installing Python dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

REM Download spaCy model
echo [3/4] Downloading spaCy English model...
python -m spacy download en_core_web_sm
if errorlevel 1 (
    echo ERROR: Failed to download spaCy model.
    pause
    exit /b 1
)

REM Train the ML classifier
echo [4/4] Training the ML classifier...
python scripts\train_classifier.py
if errorlevel 1 (
    echo WARNING: ML classifier training failed. The system will try to auto-train on first run.
)

echo.
echo ============================================
echo   Setup complete! Run 'run.bat' to start.
echo ============================================
pause
