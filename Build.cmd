@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name HeyouCapture --collect-all customtkinter --icon assets\heyou.ico --add-data "assets;assets" --add-data "automation.ps1;." app.py
if errorlevel 1 exit /b 1
echo Application: dist\HeyouCapture\HeyouCapture.exe
