@echo off
cd /d "%~dp0"
title Configuration LogMed RAPP
echo ===================================================
echo     LogMed RAPP - Configuration de l'environnement
echo ===================================================
echo.

if not exist ".venv" (
    echo [1/3] Creation de l'environnement virtuel .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERREUR] Python 3.9+ n'est pas installe ou non present dans le PATH.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Environnement .venv deja present.
)

echo.
echo [2/3] Mise a jour de pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo [3/3] Installation des dependances (PyQt5, pandas, openpyxl, rapidfuzz)...
.venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ===================================================
echo   [SUCCES] LogMed RAPP est pret a etre utilise !
echo   Vous pouvez double-cliquer sur 'run_app.bat'.
echo ===================================================
pause
