@echo off
cd /d "%~dp0"
title Compilation LogMed RAPP (Fichier Unique)

if not exist ".venv\Scripts\pyinstaller.exe" (
    echo Installation de PyInstaller...
    .venv\Scripts\pip.exe install pyinstaller
)

echo Compilation en un fichier executable unique...
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed --name "LogMed_RAPP" --icon "assets\app_icon.ico" --add-data "assets;assets" main.py

echo.
echo =======================================================
echo   [SUCCES] Executable unique cree : dist\LogMed_RAPP.exe
echo =======================================================
pause
