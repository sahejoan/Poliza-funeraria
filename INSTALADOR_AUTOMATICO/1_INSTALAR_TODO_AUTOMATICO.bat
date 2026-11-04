@echo off
chcp 65001 > nul
title Instalador Automático - Memoriales Altagracia
color 0A

echo ======================================================================
echo       INSTALADOR AUTOMATICO - SISTEMA MEMORIALES ALTAGRACIA
echo ======================================================================
echo.
echo Iniciando proceso de instalacion...
echo Por favor espera unos segundos mientras se prepara el entorno.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"

if %errorlevel% neq 0 (
    echo.
    echo [ADVERTENCIA] Ocurrio un detalle durante la ejecucion.
    pause
)

