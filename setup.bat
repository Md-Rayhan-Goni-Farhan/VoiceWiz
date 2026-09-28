@echo off
title VoiceWiz Setup
echo ============================================
echo       VoiceWiz — Setting up environment
echo ============================================
echo.
echo This will take 5-15 minutes depending on your internet speed.
echo Do NOT close this window.
echo.

cd /d "%~dp0"

echo [1/4] Creating Python environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.12 from python.org
    pause
    exit /b 1
)

echo [2/4] Activating environment...
call venv\Scripts\activate.bat

echo [3/4] Installing packages...
pip install numpy==1.26.4
pip install torch==2.4.0+cpu torchaudio==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
pip install scipy==1.13.1 librosa==0.10.2 soundfile sounddevice pydub customtkinter Pillow munch==4.0.0 einops==0.8.0 descript-audio-codec transformers==4.46.3 huggingface-hub praat-parselmouth pyworld resemblyzer
pip install numpy==1.26.4 --force-reinstall --no-deps

echo [4/4] Cloning voice engine...
git clone https://github.com/Plachtaa/seed-vc.git
pip install munch

echo.
echo ============================================
echo   Setup complete! Launching VoiceWiz...
echo ============================================
timeout /t 2
python voicewiz.py