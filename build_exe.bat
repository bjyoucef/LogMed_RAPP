@echo off
cd /d "%~dp0"
title Compilation LogMed RAPP

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo Installation de PyInstaller...
    .venv\Scripts\pip.exe install pyinstaller
)

echo Compilation en cours...
.venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed --name "LogMed_RAPP" main.py

echo.
echo ===================================================
echo   [SUCCES] Executable cree dans dist\LogMed_RAPP\
echo ===================================================
pause
