@echo off
chcp 65001 > nul
title Memoriales Altagracia - Sistema de Gestión Funeraria
color 0B

set "SISTEMA_DIR=%~dp0SYSTEMFN"
set "PYTHON312_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
if exist "%PYTHON312_DIR%\python.exe" set "PATH=%PYTHON312_DIR%;%PYTHON312_DIR%\Scripts;%PATH%"

cd /d "%SISTEMA_DIR%"

where python >nul 2>&1
if %errorlevel% equ 0 (
    python main.py
    goto FIN
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 main.py
    goto FIN
)

echo [ERROR] No se detecto Python instalado en el equipo.
echo Por favor ejecuta primero el instalador:
echo Carpeta "INSTALADOR_AUTOMATICO" -> "1_INSTALAR_TODO_AUTOMATICO.bat"
echo.
pause

:FIN
if %errorlevel% neq 0 (
    echo.
    echo Ocurrio un error al ejecutar el sistema.
    pause
)
