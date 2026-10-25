@echo off
cd /d "%~dp0"
title Lancement de LogMed RAPP

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Premier lancement detecte. Configuration en cours...
    call setup_env.bat
)

echo Lancement de LogMed RAPP...
start "" .venv\Scripts\python.exe main.py
