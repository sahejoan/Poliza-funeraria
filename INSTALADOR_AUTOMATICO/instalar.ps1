# ==============================================================================
# Script de Instalación Automatizada - Sistema Memoriales Altagracia
# ==============================================================================
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Instalador Automático - Memoriales Altagracia"

function Escribir-Titulo {
    Clear-Host
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "      INSTALADOR AUTOMATICO - SISTEMA MEMORIALES ALTAGRACIA           " -ForegroundColor Yellow
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host ""
}

Escribir-Titulo
Write-Host "Iniciando proceso de preparacion e instalacion del sistema..." -ForegroundColor White
Write-Host "Este instalador configurara todo de manera automatica." -ForegroundColor Gray
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir
$SystemDir = Join-Path $RootDir "SYSTEMFN"

if (-not (Test-Path $SystemDir)) {
    Write-Host "[ERROR CRITICO] No se encontro la carpeta del sistema en: $SystemDir" -ForegroundColor Red
    pause
    exit 1
}

# ------------------------------------------------------------------------------
# 1. DETECCIÓN Y/O INSTALACIÓN DE PYTHON
# ------------------------------------------------------------------------------
Write-Host "======================================================================" -ForegroundColor DarkCyan
Write-Host "[1/4] Verificando instalacion de Python en este equipo..." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkCyan

function Obtener-PythonExe {
    # Prefer the user-installed Python required by pandas 3.x.
    $python312 = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path $python312) {
        return $python312
    }

    # 1. Comprobar si python está en PATH
    $cmd = Get-Command "python" -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    
    # 2. Comprobar py launcher
    $pyCmd = Get-Command "py" -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $pyPath = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($pyPath -and (Test-Path $pyPath)) {
            return $pyPath.Trim()
        }
    }

    # 3. Comprobar rutas tipicas en LocalAppData
    $rutasLocales = Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    if ($rutasLocales) {
        return ($rutasLocales | Select-Object -First 1)
    }

    # 4. Comprobar rutas en Archivos de Programa
    $rutasProgram = Get-ChildItem -Path "C:\Program Files\Python*" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    if ($rutasProgram) {
        return ($rutasProgram | Select-Object -First 1)
    }

    return $null
}

$PythonExe = Obtener-PythonExe

if (-not $PythonExe) {
    Write-Host "[!] Python no esta instalado o no se encuentra en el sistema." -ForegroundColor Yellow
    Write-Host "[+] Descargando instalador oficial de Python para Windows (64-bit)..." -ForegroundColor Cyan
    
    $PythonUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $InstallerPath = Join-Path $env:TEMP "python-installer-memoriales.exe"
    
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $PythonUrl -OutFile $InstallerPath -UseBasicParsing
        Write-Host "[OK] Descarga de Python completada." -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] No se pudo descargar Python automaticamente: $_" -ForegroundColor Red
        Write-Host "Por favor descarga e instala Python manualmente desde: https://www.python.org/downloads/" -ForegroundColor Yellow
        pause
        exit 1
    }

    Write-Host "[+] Instalando Python automaticamente (marcando agregar a PATH)..." -ForegroundColor Cyan
    Write-Host "Por favor espere unos instantes mientras Windows realiza la instalacion..." -ForegroundColor Gray
    
    # Argumentos para instalación silenciosa / pasiva con PATH activado
    $installArgs = "/passive InstallAllUsers=0 PrependPath=1 Include_pip=1 SimpleInstall=1"
    $process = Start-Process -FilePath $InstallerPath -ArgumentList $installArgs -Wait -PassThru

    Start-Sleep -Seconds 3

    # Refrescar PATH de la sesion actual desde el registro de Windows
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"

    $PythonExe = Obtener-PythonExe
    if (-not $PythonExe) {
        Write-Host "[ADVERTENCIA] Python se instalo, pero puede requerir reiniciar la terminal para actualizar el PATH." -ForegroundColor Yellow
    }
}

if ($PythonExe) {
    $versionOutput = & $PythonExe --version 2>&1
    Write-Host "[OK] Python detectado: $versionOutput" -ForegroundColor Green
    Write-Host "     Ruta: $PythonExe" -ForegroundColor Gray
} else {
    Write-Host "[ERROR] No fue posible localizar el ejecutable de Python. Por favor verifica la instalacion." -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""

# ------------------------------------------------------------------------------
# 2. INSTALACIÓN DE LIBRERÍAS Y DEPENDENCIAS
# ------------------------------------------------------------------------------
Write-Host "======================================================================" -ForegroundColor DarkCyan
Write-Host "[2/4] Instalando librerias y dependencias necesarias..." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkCyan

Write-Host "[+] Actualizando pip e instalando dependencias requeridas..." -ForegroundColor Cyan
Write-Host "     - customtkinter (interfaz grafica moderna)" -ForegroundColor Gray
Write-Host "     - reportlab (generacion de contratos PDF)" -ForegroundColor Gray
Write-Host "     - pandas y openpyxl (exportacion de reportes Excel)" -ForegroundColor Gray
Write-Host "     - Pillow (manejo de imagenes y logos)" -ForegroundColor Gray
Write-Host ""

& $PythonExe -m pip install --upgrade pip --quiet
$librerias = @("customtkinter>=5.2.0", "reportlab>=4.0.0", "pandas", "openpyxl", "Pillow")

foreach ($lib in $librerias) {
    Write-Host "Instalando $lib..." -NoNewline
    $res = & $PythonExe -m pip install $lib --quiet 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " [LISTO]" -ForegroundColor Green
    } else {
        Write-Host " [REINTENTANDO]" -ForegroundColor Yellow
        & $PythonExe -m pip install $lib
    }
}

Write-Host ""

# ------------------------------------------------------------------------------
# 3. VERIFICACIÓN DEL SISTEMA
# ------------------------------------------------------------------------------
Write-Host "======================================================================" -ForegroundColor DarkCyan
Write-Host "[3/4] Verificando que todo funcione correctamente..." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkCyan

$testScript = @"
import sys
try:
    import customtkinter
    import reportlab
    import pandas
    import openpyxl
    import PIL
    import sqlite3
    print('VERIFICACION_EXITOSA')
except Exception as e:
    print('ERROR:', e)
    sys.exit(1)
"@

$checkResult = & $PythonExe -c $testScript 2>&1
if ($checkResult -match "VERIFICACION_EXITOSA") {
    Write-Host "[OK] Todas las librerias se cargaron y verificaron correctamente al 100%." -ForegroundColor Green
} else {
    Write-Host "[ADVERTENCIA] Hubo una alerta en la verificacion: $checkResult" -ForegroundColor Yellow
}

Write-Host ""

# ------------------------------------------------------------------------------
# 4. CREACIÓN DE ACCESOS DIRECTOS Y LANZADORES
# ------------------------------------------------------------------------------
Write-Host "======================================================================" -ForegroundColor DarkCyan
Write-Host "[4/4] Creando accesos directos..." -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor DarkCyan

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $DesktopPath "Memoriales Altagracia.lnk"
    
    $LauncherBat = Join-Path $RootDir "ABRIR_SISTEMA.bat"

    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $LauncherBat
    $Shortcut.WorkingDirectory = $SystemDir
    $Shortcut.Description = "Sistema de Gestion Funeraria - Memoriales Altagracia"
    $Shortcut.Save()

    Write-Host "[OK] Acceso directo creado en el Escritorio: 'Memoriales Altagracia'" -ForegroundColor Green
} catch {
    Write-Host "[INFO] No se pudo crear el acceso en el escritorio, pero podras abrir el sistema desde la carpeta." -ForegroundColor Gray
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "           ¡INSTALACION COMPLETADA EXITOSAMENTE!                     " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "PRIMER INICIO:" -ForegroundColor Yellow
Write-Host "  Al abrir el sistema, crea un usuario y una contrasena de administrador." -ForegroundColor White
Write-Host "  La contrasena debe tener al menos 12 caracteres; no hay una clave predeterminada." -ForegroundColor White
Write-Host ""
Write-Host "COMO ABRIR EL PROGRAMA:" -ForegroundColor Cyan
Write-Host "  1. Haz doble clic en el acceso directo 'Memoriales Altagracia' en tu Escritorio." -ForegroundColor White
Write-Host "  2. O haz doble clic en 'ABRIR_SISTEMA.bat' en la carpeta principal." -ForegroundColor White
Write-Host ""

$abrirAhora = Read-Host "¿Deseas abrir el sistema ahora mismo? (S/N)"
if ($abrirAhora -eq "S" -or $abrirAhora -eq "s") {
    Write-Host "Iniciando Memoriales Altagracia..." -ForegroundColor Cyan
    Start-Process -FilePath $PythonExe -ArgumentList "main.py" -WorkingDirectory $SystemDir
}

Write-Host "Presione cualquier tecla para cerrar el instalador..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
