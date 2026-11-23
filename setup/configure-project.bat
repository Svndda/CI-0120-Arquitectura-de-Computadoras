@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."
if not exist "rv32i-project\simics.bat" (
    echo [ERROR] No se encontro rv32i-project. Ejecuta este script desde la raiz del repositorio.
    exit /b 1
)

set "PROJECT_DIR=%CD%\rv32i-project"
set "SIMICS_BASE=C:\Users\%USERNAME%\AppData\Local\Programs\Simics\simics-7.113.0"
set "USER_PYTHON=C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.14-64\python.exe"

echo.
echo =========================================================================
echo  RV32I RISC-V Core - Configuracion de rutas para el usuario actual
echo =========================================================================
echo.
echo Usuario actual:    %USERNAME%
echo Proyecto:          %PROJECT_DIR%
echo Simics base:       %SIMICS_BASE%
echo Python usuario:    %USER_PYTHON%
echo.

if not exist "%SIMICS_BASE%\bin\simics.bat" (
    echo [ADVERTENCIA] Simics no se encontro en:
    echo               %SIMICS_BASE%
    echo               Instala Simics primero (ver simics_installation.pdf y SETUP_PROCESS.md).
    echo               Los .bat se configuraran con esta ruta de todas formas; ajustala si es diferente.
    echo.
    set /p "CONTINUAR=¿Continuar igual? (s/N): "
    if /I "!CONTINUAR!" neq "s" (
        echo Configuracion cancelada.
        exit /b 1
    )
)

echo [1/6] Ajustando rutas en simics.bat...
call :replace_paths "rv32i-project\simics.bat"

echo [2/6] Ajustando rutas en bin\make.bat...
call :replace_paths "rv32i-project\bin\make.bat"

echo [3/6] Ajustando rutas en bin\mini-python.bat...
call :replace_paths "rv32i-project\bin\mini-python.bat"

echo [4/6] Ajustando rutas en bin\project-setup.bat...
call :replace_paths "rv32i-project\bin\project-setup.bat"

echo [5/6] Ajustando rutas en bin\setup-venv.bat...
call :replace_paths "rv32i-project\bin\setup-venv.bat"

echo [6/6] Ajustando rutas en config.mk...
call :replace_paths "rv32i-project\config.mk"

echo.
echo [7/7] Creando entorno virtual e instalando dependencias Python...

if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo       .venv ya existe. Saltando creacion.
) else (
    if exist "%SIMICS_BASE%\bin\setup-venv.bat" (
        echo       Ejecutando setup-venv.bat de Simics...
        call "%SIMICS_BASE%\bin\setup-venv.bat" "%PROJECT_DIR%"
        if %errorlevel% neq 0 (
            echo       AVISO: setup-venv.bat de Simics fallo. Intentando python -m venv...
        )
    )
    if not exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
        where python >nul 2>&1
        if %errorlevel% equ 0 (
            python -m venv "%PROJECT_DIR%\.venv"
        ) else (
            echo       AVISO: No se encontro Python para crear el .venv.
        )
    )
)

if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    echo       OK: .venv creado en %PROJECT_DIR%\.venv

    echo       Instalando dependencias de requirements.txt...
    if exist "%PROJECT_DIR%\requirements.txt" (
        "%PROJECT_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
        "%PROJECT_DIR%\.venv\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\requirements.txt" >nul 2>&1
    )

    echo       Instalando dependencias de gui-requirements.txt (wxPython - solo GUI)...
    if exist "%PROJECT_DIR%\gui-requirements.txt" (
        "%PROJECT_DIR%\.venv\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\gui-requirements.txt" >nul 2>&1
        if %errorlevel% equ 0 (
            echo       OK: wxPython instalado.
        ) else (
            echo       AVISO: wxPython no se instalo (opcional, solo para GUI).
        )
    )
) else (
    echo       AVISO: No se pudo crear el .venv. Los tests usaran python.bat de Simics.
)

echo.
echo =========================================================================
echo  Configuracion completada.
echo =========================================================================
echo.
echo Pruebas rápidas:
echo   cd rv32i-project
echo   run-rv32i.bat build
echo   run-rv32i.bat tests all
echo.
pause
exit /b 0

:replace_paths
set "FILE=%~1"
if not exist "%FILE%" exit /b 0

set "PS_FILE=%FILE%"
set "PS_OLD_SIMICS=C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0"
set "PS_NEW_SIMICS=%SIMICS_BASE%"
set "PS_OLD_PROJECT=E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project"
set "PS_NEW_PROJECT=%PROJECT_DIR%"
set "PS_OLD_PYTHON=C:\Users\aaron\AppData\Local\Python\pythoncore-3.14-64\python.exe"
set "PS_NEW_PYTHON=%USER_PYTHON%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = $env:PS_FILE;" ^
    "$c = Get-Content -Path $p -Raw;" ^
    "$c = $c -replace [regex]::Escape($env:PS_OLD_SIMICS), $env:PS_NEW_SIMICS;" ^
    "$c = $c -replace [regex]::Escape($env:PS_OLD_PROJECT), $env:PS_NEW_PROJECT;" ^
    "$c = $c -replace [regex]::Escape($env:PS_OLD_PYTHON), $env:PS_NEW_PYTHON;" ^
    "[System.IO.File]::WriteAllText($p, $c)"

if %errorlevel% neq 0 (
    echo       [ADVERTENCIA] No se pudo procesar %FILE% con PowerShell.
) else (
    echo       OK: %FILE%
)
exit /b 0
