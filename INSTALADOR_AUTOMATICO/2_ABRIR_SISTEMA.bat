@echo off
chcp 65001 > nul
title Memoriales Altagracia - Sistema de Gestión Funeraria
color 0B

set "DIR_ACTUAL=%~dp0"
set "ROOT_DIR=%DIR_ACTUAL%..\"
set "SISTEMA_DIR=%ROOT_DIR%SYSTEMFN"
set "PYTHON312_DIR=%LOCALAPPDATA%\Programs\Python\Python312"
if exist "%PYTHON312_DIR%\python.exe" set "PATH=%PYTHON312_DIR%;%PYTHON312_DIR%\Scripts;%PATH%"

cd /d "%SISTEMA_DIR%"

:: Buscar Python
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

echo [ERROR] No se encontro Python en el sistema.
echo Por favor ejecuta primero '1_INSTALAR_TODO_AUTOMATICO.bat'.
echo.
pause

:FIN
if %errorlevel% neq 0 (
    echo.
    echo Ocurrio un error al ejecutar el sistema.
    pause
)
