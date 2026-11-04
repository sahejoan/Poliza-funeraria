@echo off
chcp 65001 > nul
title Instalador y Ejecutador - Memoriales Altagracia
color 0B

set "PYTHON312_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
if exist "%PYTHON312_DIR%\python.exe" set "PATH=%PYTHON312_DIR%;%PYTHON312_DIR%\Scripts;%PATH%"
cd /d "%~dp0"

echo ========================================================
echo   SISTEMA DE GESTION FUNERARIA - MEMORIALES ALTAGRACIA
echo ========================================================
echo.

:: Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se detecto Python instalado en el sistema.
    echo.
    echo Por favor, instala Python 3.10, 3.11, 3.12 o superior desde:
    echo https://www.python.org/downloads/
    echo Asegurate de marcar la casilla: "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b
)

echo [1/3] Verificando instalacion de Python...
python --version
echo.

echo [2/3] Instalando librerias necesarias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ADVERTENCIA] Ocurrio un inconveniente instalando dependencias.
    echo Intentando instalacion individual...
    python -m pip install customtkinter reportlab pandas openpyxl Pillow
)

echo.
echo [3/3] Iniciando el Sistema Memoriales Altagracia...
echo ========================================================
python main.py

if %errorlevel% neq 0 (
    echo.
    echo Ocurrio un error al ejecutar el programa.
    pause
)
