@echo off
cd /d "%~dp0"
if exist ".build-deps" set "PYTHONPATH=%~dp0.build-deps;%PYTHONPATH%"
python app.py
if errorlevel 1 pause
